"""AlertRide core logic: EAR, the drowsiness state machine, and the serial link.

Kept separate from the camera and the dashboard so it can be unit-tested
without a webcam or a board attached. See tests/test_logic.py.
"""
from __future__ import annotations

import math
import time
from collections import deque

# --- states, matching the firmware protocol in firmware/esp32_alert -------
AWAKE   = "AWAKE"
WARNING = "WARNING"
DROWSY  = "DROWSY"
NO_FACE = "NO_FACE"

# One name per state everywhere. The original drowsiness_test.py assigned
# "BEEP" / "ALARM+VIBRATION" but tested for "WARNING" / "DROWSY", so neither
# branch ever matched and both alert stages were silently dead.
COMMAND = {AWAKE: "A", WARNING: "W", DROWSY: "D", NO_FACE: "S"}

# --- eye landmarks, 478-point MediaPipe face mesh ------------------------
# Six points per eye in EAR order: outer, upper-outer, upper-inner, inner,
# lower-inner, lower-outer.
LEFT_EYE  = (33, 160, 158, 133, 153, 144)
RIGHT_EYE = (362, 385, 387, 263, 373, 380)


def _dist(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def eye_aspect_ratio(pts) -> float:
    """Soukupova & Cech eye aspect ratio for one eye.

    pts is six (x, y) pairs in the order above. Returns roughly 0.3 for an
    open eye and under 0.15 for a closed one, but the absolute value depends
    on face shape, glasses and camera angle - which is why the threshold is
    calibrated per person rather than hardcoded.
    """
    p1, p2, p3, p4, p5, p6 = pts
    horizontal = _dist(p1, p4)
    if horizontal == 0:
        return 0.0
    return (_dist(p2, p6) + _dist(p3, p5)) / (2.0 * horizontal)


def both_eyes_ear(landmarks) -> float:
    """Mean EAR across both eyes. landmarks is indexable by mesh index."""
    left = eye_aspect_ratio([landmarks[i] for i in LEFT_EYE])
    right = eye_aspect_ratio([landmarks[i] for i in RIGHT_EYE])
    return (left + right) / 2.0


class DrowsinessState:
    """Turns a stream of EAR samples into AWAKE / WARNING / DROWSY.

    Escalation is by *duration of closure*, not by EAR alone: a normal blink
    is 100-400 ms, so anything under warn_after is ignored. That is the whole
    reason this is a state machine and not an if-statement on the EAR.
    """

    def __init__(self, threshold=0.25, warn_after=1.0, drowsy_after=2.0,
                 no_face_after=1.0):
        self.threshold = threshold
        self.warn_after = warn_after
        self.drowsy_after = drowsy_after
        self.no_face_after = no_face_after

        self.state = AWAKE
        self.closed_since = None
        self.last_face_at = None
        self.ear = None

    def update(self, ear, now=None):
        """Feed one frame. ear is None when no face was found."""
        now = time.monotonic() if now is None else now
        self.ear = ear

        if ear is None:
            if self.last_face_at is None:
                self.last_face_at = now
            if now - self.last_face_at >= self.no_face_after:
                self.closed_since = None
                self.state = NO_FACE
            return self.state

        self.last_face_at = now

        if ear >= self.threshold:
            self.closed_since = None
            self.state = AWAKE
            return self.state

        if self.closed_since is None:
            self.closed_since = now
        closed_for = now - self.closed_since

        if closed_for >= self.drowsy_after:
            self.state = DROWSY
        elif closed_for >= self.warn_after:
            self.state = WARNING
        else:
            # Still inside blink territory - do not alert.
            self.state = AWAKE
        return self.state

    @property
    def closed_for(self):
        if self.closed_since is None:
            return 0.0
        return time.monotonic() - self.closed_since


class BoardLink:
    """Serial link to the ESP32, or a no-op when no board is attached.

    Transmits on state change and once a second as a keepalive. The keepalive
    is not optional: the firmware's link-timeout failsafe stops the buzzer and
    motor after three seconds of silence, so a long steady DROWSY would
    otherwise switch itself off mid-alert.
    """

    KEEPALIVE_S = 1.0

    def __init__(self, port=None, baud=115200, timeout=0.1):
        self.port_name = port
        self.baud = baud
        self.timeout = timeout
        self.ser = None
        self.error = None
        self.last_sent = None
        self.last_sent_at = 0.0
        self.replies = deque(maxlen=200)

    # -- connection -------------------------------------------------------
    @staticmethod
    def find_port():
        """Locate the ESP32 by its USB bridge chip, never by a fixed COMn.

        Windows assigns the number per USB socket, so a hardcoded port breaks
        the moment the cable moves. On this project's machine COM3-COM6 are
        Bluetooth serial, so a hardcoded "COM6" opens a Bluetooth channel and
        hangs with no error at all.
        """
        try:
            from serial.tools import list_ports
        except ImportError:
            return None
        known = {(0x10C4, 0xEA60),  # Silicon Labs CP210x
                 (0x1A86, 0x7523),  # CH340
                 (0x0403, 0x6001)}  # FTDI FT232
        for p in list_ports.comports():
            if (p.vid, p.pid) in known:
                return p.device
        for p in list_ports.comports():
            blurb = f"{p.description} {p.manufacturer}".lower()
            if any(k in blurb for k in ("cp210", "ch340", "ftdi", "silicon labs")):
                return p.device
        return None

    def connect(self):
        try:
            import serial
        except ImportError:
            self.error = "pyserial is not installed (pip install pyserial)"
            return False

        port = self.port_name or self.find_port()
        if not port:
            self.error = "No ESP32 found. Check the cable and the CP210x driver."
            return False

        try:
            self.ser = serial.Serial(port, self.baud, timeout=self.timeout)
        except Exception as exc:
            if "PermissionError" in type(exc).__name__ or "Access is denied" in str(exc):
                self.error = (f"{port} is held by another program. Close the "
                              f"Arduino Serial Monitor and try again.")
            else:
                self.error = f"Could not open {port}: {exc}"
            self.ser = None
            return False

        self.port_name = port
        time.sleep(2.0)   # the board resets when the port opens
        self.ser.reset_input_buffer()
        return True

    @property
    def connected(self):
        return self.ser is not None and self.ser.is_open

    # -- traffic ----------------------------------------------------------
    def send_state(self, state, force=False, now=None):
        """Send the command for `state`, on change or as a keepalive."""
        now = time.monotonic() if now is None else now
        cmd = COMMAND.get(state)
        if cmd is None:
            # Never fail quietly here. A state-name mismatch is exactly what
            # silently disabled both alert stages in the original
            # drowsiness_test.py: it set "BEEP"/"ALARM+VIBRATION" but tested
            # for "WARNING"/"DROWSY", so no branch ever matched and nothing
            # said so. Loud is better than a dead alert.
            raise ValueError(
                f"Unknown state {state!r}. Use one of: {sorted(COMMAND)}. "
                f"(These are state names, not the board's reply words.)")
        due = (force or cmd != self.last_sent
               or now - self.last_sent_at >= self.KEEPALIVE_S)
        if not due:
            return False
        self.last_sent, self.last_sent_at = cmd, now
        if not self.connected:
            return False
        try:
            self.ser.write(cmd.encode())
            return True
        except Exception as exc:
            self.error = f"Write failed: {exc}"
            self.ser = None
            return False

    def read_replies(self):
        """Drain whatever the board has said. Never blocks for long."""
        out = []
        if not self.connected:
            return out
        try:
            while self.ser.in_waiting:
                line = self.ser.readline().decode(errors="replace").strip()
                if line:
                    out.append(line)
                    self.replies.append((time.time(), line))
        except Exception as exc:
            self.error = f"Read failed: {exc}"
            self.ser = None
        return out

    def close(self):
        if self.connected:
            try:
                self.ser.write(b"S")
                self.ser.flush()
                time.sleep(0.05)
            except Exception:
                pass
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None

    def connect_simulated(self):
        """Attach a software ESP32 instead of a real one (--sim)."""
        from esp32_sim import FakeSerial
        self.ser = FakeSerial()
        self.port_name = "SIM"
        self.error = None
        return True

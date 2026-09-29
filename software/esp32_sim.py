"""A software stand-in for the ESP32, mirroring firmware/esp32_alert.

It implements the same protocol and the same link-timeout failsafe, behind an
object that quacks like a pyserial Serial. That means the whole Python side -
camera, state machine, dashboard - can be built and demonstrated with no board
plugged in, and the serial contract can be tested automatically.

It is a model of the firmware, not proof the firmware is correct. If you change
one, change the other.
"""
from __future__ import annotations

import time
from collections import deque

LINK_TIMEOUT_S = 3.0     # LINK_TIMEOUT_MS in the sketch
MOTOR_PULSE_S = 0.4      # MOTOR_PULSE_MS
BLINK_PERIOD_S = 0.12    # millis()/120 in the sketch


class FakeESP32:
    """The firmware's behaviour, with the outputs readable for assertions."""

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self.green = False
        self.red = False
        self.buzzer_hz = 0
        self.motor = False
        self.state = "S"
        self._motor_pulse_until = 0.0
        self._buzz_until = None
        self._last_command_at = self._clock()
        self.out = deque()
        self._boot()

    # -- outputs ----------------------------------------------------------
    def _all_off(self):
        self.green = self.red = self.motor = False
        self.buzzer_hz = 0
        self._buzz_until = None
        self._motor_pulse_until = 0.0

    def _boot(self):
        self._all_off()
        self.out.append("AlertRide ready")

    def apply(self, c):
        now = self._clock()
        self.state = c
        if c == "A":
            self.green, self.red, self.motor = True, False, False
            self.buzzer_hz, self._buzz_until = 0, None
            self._motor_pulse_until = 0.0
            self.out.append("AWAKE")
        elif c == "W":
            self.green, self.red = False, True
            self.buzzer_hz, self._buzz_until = 1800, now + 0.25
            self.motor = True
            self._motor_pulse_until = now + MOTOR_PULSE_S
            self.out.append("WARNING")
        elif c == "D":
            self.green = False
            self.buzzer_hz, self._buzz_until = 2200, None
            self.motor = True
            self._motor_pulse_until = 0.0
            self.out.append("DROWSY")
        elif c == "S":
            self._all_off()
            self.out.append("STOPPED")

    def tick(self):
        now = self._clock()
        if self._motor_pulse_until and now >= self._motor_pulse_until:
            self.motor = False
            self._motor_pulse_until = 0.0
        if self._buzz_until is not None and now >= self._buzz_until:
            self.buzzer_hz, self._buzz_until = 0, None
        if self.state == "D":
            self.red = int(now / BLINK_PERIOD_S) % 2 == 1
        if (self.state in ("W", "D")
                and now - self._last_command_at > LINK_TIMEOUT_S):
            self._all_off()
            self.state = "S"
            self.out.append("LINK_LOST")

    # -- serial side ------------------------------------------------------
    def feed(self, data: bytes):
        for byte in data:
            c = chr(byte)
            if c in "\r\n":
                continue
            self._last_command_at = self._clock()
            if c == "?":
                self.out.append("AlertRide ready")
            elif c in "AWDS":
                self.apply(c)


class FakeSerial:
    """Minimal pyserial-compatible wrapper around FakeESP32."""

    def __init__(self, clock=time.monotonic):
        self.board = FakeESP32(clock=clock)
        self.is_open = True
        self._buf = b""

    def _pump(self):
        self.board.tick()
        while self.board.out:
            self._buf += self.board.out.popleft().encode() + b"\r\n"

    @property
    def in_waiting(self):
        self._pump()
        return len(self._buf)

    def write(self, data):
        if not self.is_open:
            raise RuntimeError("port is closed")
        self.board.feed(data)
        return len(data)

    def readline(self):
        self._pump()
        idx = self._buf.find(b"\n")
        if idx < 0:
            line, self._buf = self._buf, b""
            return line
        line, self._buf = self._buf[:idx + 1], self._buf[idx + 1:]
        return line

    def reset_input_buffer(self):
        self._buf = b""

    def flush(self):
        pass

    def close(self):
        self.is_open = False

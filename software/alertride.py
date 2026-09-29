"""AlertRide: webcam -> eye aspect ratio -> state machine -> ESP32.

    python alertride.py                 # camera + board, auto-detect port
    python alertride.py --port COM9
    python alertride.py --sim           # no board; software ESP32
    python alertride.py --no-camera     # board only, keyboard-driven
    python alertride.py --no-dashboard

Runs whatever half is available: camera with no board, or board with no
camera. Opens a live dashboard at http://127.0.0.1:8000 .

Keys in the camera window: q quit, c calibrate, [ ] nudge the threshold.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import threading
import time
import webbrowser
from collections import deque
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from core import (AWAKE, DROWSY, NO_FACE, WARNING, BoardLink, DrowsinessState,
                  both_eyes_ear)

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "face_landmarker.task")
LOG_DIR = os.path.join(HERE, "logs")


# ---------------------------------------------------------------- telemetry
class Telemetry:
    """Everything the dashboard shows. One lock, written by the main loop."""

    def __init__(self, maxlen=600):
        self.lock = threading.Lock()
        self.history = deque(maxlen=maxlen)     # (t, ear or None)
        self.events = deque(maxlen=60)
        self.snapshot = {
            "state": AWAKE, "ear": None, "threshold": 0.25, "fps": 0.0,
            "closed_for": 0.0, "camera": False, "board": False,
            "port": None, "error": None, "started": time.time(),
            "counts": {AWAKE: 0, WARNING: 0, DROWSY: 0, NO_FACE: 0},
            "last_reply": None,
        }

    def update(self, **kw):
        with self.lock:
            self.snapshot.update(kw)

    def push(self, ear):
        with self.lock:
            self.history.append((time.time(), ear))

    def event(self, kind, text):
        with self.lock:
            self.events.appendleft({"t": time.time(), "kind": kind, "text": text})

    def count(self, state):
        with self.lock:
            self.snapshot["counts"][state] = self.snapshot["counts"].get(state, 0) + 1

    def as_json(self):
        with self.lock:
            snap = dict(self.snapshot)
            snap["history"] = [{"t": t, "ear": e} for t, e in self.history]
            snap["events"] = list(self.events)
            snap["now"] = time.time()
            return json.dumps(snap)


# --------------------------------------------------------------- dashboard
def start_dashboard(telemetry, port=8000):
    page = os.path.join(HERE, "dashboard.html")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):          # keep the console clean
            pass

        def do_GET(self):
            if self.path.startswith("/api/state"):
                body = telemetry.as_json().encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            try:
                with open(page, "rb") as fh:
                    body = fh.read()
            except OSError:
                self.send_error(404, "dashboard.html is missing")
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    try:
        srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError as exc:
        print(f"  dashboard: port {port} unavailable ({exc})")
        return None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# ------------------------------------------------------------------ camera
class FaceTracker:
    """MediaPipe FaceLandmarker, Tasks API.

    The legacy mp.solutions.face_mesh API the original scripts used does not
    exist in mediapipe 1.x at all - mp.solutions was removed. This is the
    supported path. The 478-point mesh has the same topology, so the EAR
    landmark indices are unchanged.
    """

    def __init__(self, model_path=MODEL):
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"{model_path} not found. Download face_landmarker.task into "
                f"the same folder as this script - see README.md.")

        self.mp = mp
        opts = vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1)
        self.landmarker = vision.FaceLandmarker.create_from_options(opts)

    def ear_for(self, bgr_frame, timestamp_ms):
        """Return (ear, pixel_landmarks) or (None, None) when no face."""
        import cv2
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect_for_video(image, int(timestamp_ms))
        if not result.face_landmarks:
            return None, None
        h, w = bgr_frame.shape[:2]
        pts = [(lm.x * w, lm.y * h) for lm in result.face_landmarks[0]]
        return both_eyes_ear(pts), pts

    def close(self):
        # Explicit teardown. Left to __del__, mediapipe's finaliser runs after
        # module globals are gone and raises a confusing TypeError on exit.
        try:
            self.landmarker.close()
        except Exception:
            pass


# -------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="AlertRide drowsiness detector")
    ap.add_argument("--port", help="serial port (default: find by chip ID)")
    ap.add_argument("--sim", action="store_true", help="software ESP32")
    ap.add_argument("--no-camera", action="store_true")
    ap.add_argument("--no-dashboard", action="store_true")
    ap.add_argument("--camera-index", type=int, default=0)
    ap.add_argument("--threshold", type=float, default=0.25)
    ap.add_argument("--warn-after", type=float, default=1.0)
    ap.add_argument("--drowsy-after", type=float, default=2.0)
    ap.add_argument("--dashboard-port", type=int, default=8000)
    args = ap.parse_args()

    telemetry = Telemetry()
    machine = DrowsinessState(threshold=args.threshold,
                              warn_after=args.warn_after,
                              drowsy_after=args.drowsy_after)
    telemetry.update(threshold=args.threshold)

    print("AlertRide")
    print("=" * 46)

    # --- board ---------------------------------------------------------
    link = BoardLink(port=args.port)
    if args.sim:
        link.connect_simulated()
        print("  board:     simulated (no hardware in the loop)")
    elif link.connect():
        print(f"  board:     {link.port_name} @ {link.baud}")
    else:
        print(f"  board:     not connected - {link.error}")
        print("             Running camera-only; alerts will show on screen.")
    telemetry.update(board=link.connected, port=link.port_name, error=link.error)

    # --- camera --------------------------------------------------------
    cap = tracker = cv2 = None
    if not args.no_camera:
        try:
            import cv2 as _cv2
            cv2 = _cv2
            if not hasattr(cv2, "imshow"):
                raise RuntimeError("headless build")
            backend = cv2.CAP_DSHOW if sys.platform == "win32" else 0
            cap = cv2.VideoCapture(args.camera_index, backend)
            if not cap.isOpened():
                raise RuntimeError(f"camera {args.camera_index} would not open")
            tracker = FaceTracker()
            print(f"  camera:    index {args.camera_index}, face mesh loaded")
        except Exception as exc:
            print(f"  camera:    unavailable - {exc}")
            if cap is not None:
                cap.release()
            cap = tracker = None
    telemetry.update(camera=cap is not None)

    if cap is None and not link.connected:
        print("\nNeither a camera nor a board. Nothing to do.")
        print("Try: python hardware_test.py --sim")
        return 2

    # --- dashboard -----------------------------------------------------
    if not args.no_dashboard:
        if start_dashboard(telemetry, args.dashboard_port):
            url = f"http://127.0.0.1:{args.dashboard_port}"
            print(f"  dashboard: {url}")
            try:
                webbrowser.open(url)
            except Exception:
                pass

    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(
        LOG_DIR, datetime.now().strftime("session-%Y%m%d-%H%M%S.csv"))
    log_file = open(log_path, "w", newline="", encoding="utf-8")
    log = csv.writer(log_file)
    log.writerow(["iso_time", "monotonic", "ear", "state", "threshold"])
    print(f"  log:       {log_path}")
    print("\n  q quit   c calibrate   [ ] threshold\n")

    telemetry.event("info", "Session started")
    if not link.connected and not args.sim:
        telemetry.event("warn", "No board - screen alerts only")

    frames = 0
    fps_at = time.monotonic()
    fps = 0.0
    last_state = None
    t0 = time.monotonic()
    calib = None

    try:
        while True:
            now = time.monotonic()
            ear = None

            if cap is not None:
                ok, frame = cap.read()
                if not ok:
                    telemetry.event("warn", "Dropped frame from the camera")
                    time.sleep(0.05)
                    continue
                frame = cv2.flip(frame, 1)
                try:
                    ear, pts = tracker.ear_for(frame, (now - t0) * 1000.0)
                except Exception as exc:
                    telemetry.event("warn", f"Face mesh error: {exc}")
                    ear, pts = None, None
            else:
                time.sleep(0.05)

            state = machine.update(ear, now=now)
            telemetry.push(ear)

            if state != last_state:
                telemetry.count(state)
                telemetry.event(
                    {AWAKE: "ok", WARNING: "warn",
                     DROWSY: "crit", NO_FACE: "info"}[state],
                    {AWAKE: "Awake", WARNING: "Warning - eyes closed 1 s",
                     DROWSY: "DROWSY - eyes closed 2 s",
                     NO_FACE: "No face in frame"}[state])
                last_state = state

            link.send_state(state, now=now)
            for line in link.read_replies():
                telemetry.update(last_reply=line)
                if line == "LINK_LOST":
                    telemetry.event("warn", "Board failsafe fired (LINK_LOST)")
                elif line == "AlertRide ready":
                    telemetry.event("warn", "Board reset - check the 5 V rail")

            log.writerow([datetime.now().isoformat(timespec="milliseconds"),
                          f"{now - t0:.3f}",
                          "" if ear is None else f"{ear:.4f}",
                          state, f"{machine.threshold:.3f}"])

            frames += 1
            if now - fps_at >= 0.5:
                fps = frames / (now - fps_at)
                frames, fps_at = 0, now

            telemetry.update(state=state, ear=ear, fps=fps,
                             threshold=machine.threshold,
                             closed_for=machine.closed_for,
                             board=link.connected, error=link.error)

            if cap is not None:
                draw(cv2, frame, state, ear, machine, fps, link, calib)
                cv2.imshow("AlertRide", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                if key == ord("c"):
                    calib = calibrate(cv2, cap, tracker, machine, telemetry, t0)
                if key == ord("["):
                    machine.threshold = round(machine.threshold - 0.01, 3)
                if key == ord("]"):
                    machine.threshold = round(machine.threshold + 0.01, 3)
    except KeyboardInterrupt:
        pass
    finally:
        telemetry.event("info", "Session ended")
        link.send_state(NO_FACE, force=True)
        time.sleep(0.1)
        link.close()
        if tracker is not None:
            tracker.close()
        if cap is not None:
            cap.release()
            cv2.destroyAllWindows()
        log_file.close()
        print(f"\nLog written: {log_path}")
        print("Record trials, false alarms, missed detections, lighting and "
              "glasses on/off alongside it.")
    return 0


def draw(cv2, frame, state, ear, machine, fps, link, calib):
    colour = {AWAKE: (12, 163, 12), WARNING: (25, 178, 250),
              DROWSY: (59, 59, 208), NO_FACE: (129, 135, 137)}[state]
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 74), (20, 20, 20), -1)
    cv2.putText(frame, state, (14, 48), cv2.FONT_HERSHEY_SIMPLEX, 1.2, colour, 3)
    txt = "EAR --.---" if ear is None else f"EAR {ear:.3f}"
    cv2.putText(frame, txt, (230, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (235, 235, 235), 1)
    cv2.putText(frame, f"thr {machine.threshold:.3f}", (230, 56),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (195, 194, 183), 1)
    cv2.putText(frame, f"{fps:4.1f} fps", (w - 210, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (195, 194, 183), 1)
    board = f"board {link.port_name}" if link.connected else "no board"
    cv2.putText(frame, board, (w - 210, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (12, 163, 12) if link.connected else (100, 100, 110), 1)
    if state in (WARNING, DROWSY):
        cv2.rectangle(frame, (2, 2), (w - 3, h - 3), colour, 6)
    if calib:
        cv2.putText(frame, f"calibrated open {calib[0]:.3f} / shut {calib[1]:.3f}",
                    (14, h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (195, 194, 183), 1)


def calibrate(cv2, cap, tracker, machine, telemetry, t0):
    """Measure this face's open and shut EAR, then set the threshold between.

    The 0.25 default is a starting point, not a correct value for your face,
    your glasses or your lighting.
    """
    def sample(prompt, seconds=3.0):
        vals, end = [], time.monotonic() + seconds
        while time.monotonic() < end:
            ok, frame = cap.read()
            if not ok:
                continue
            frame = cv2.flip(frame, 1)
            ear, _ = tracker.ear_for(frame, (time.monotonic() - t0) * 1000.0)
            if ear is not None:
                vals.append(ear)
            left = end - time.monotonic()
            cv2.putText(frame, prompt, (14, 44), cv2.FONT_HERSHEY_SIMPLEX,
                        0.9, (255, 255, 255), 2)
            cv2.putText(frame, f"{left:.1f}s", (14, 84),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
            cv2.imshow("AlertRide", frame)
            cv2.waitKey(1)
        vals.sort()
        return vals[len(vals) // 2] if vals else None

    print("\nCalibrating. Hold still.")
    open_ear = sample("EYES OPEN - look at the camera")
    shut_ear = sample("EYES SHUT - keep them closed")
    if open_ear is None or shut_ear is None or open_ear <= shut_ear:
        print("  Calibration failed - no usable face. Threshold unchanged.")
        telemetry.event("warn", "Calibration failed - face not found")
        return None
    machine.threshold = round((open_ear + shut_ear) / 2.0, 3)
    print(f"  open {open_ear:.3f}  shut {shut_ear:.3f}  "
          f"-> threshold {machine.threshold:.3f}")
    telemetry.event("ok", f"Calibrated: threshold {machine.threshold:.3f}")
    telemetry.update(threshold=machine.threshold)
    return (open_ear, shut_ear)


if __name__ == "__main__":
    sys.exit(main())

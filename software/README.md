# AlertRide — software

Webcam → eye aspect ratio → state machine → ESP32 → LEDs, buzzer, motor.
Plus a live dashboard at `http://127.0.0.1:8000`.

Hardware wiring is in [`../hardware/BREADBOARD_MAP.md`](../hardware/BREADBOARD_MAP.md).

---

## You do not need to downgrade Python

Checked against PyPI on 2026-09-29:

| Package | Windows wheel | Means |
| --- | --- | --- |
| `mediapipe` 1.0.1 | `py3-none-win_amd64` | no Python version restriction at all |
| `opencv-python` 5.0.0.93 | `cp37-abi3-win_amd64` | stable ABI, any CPython ≥ 3.7 |

Both install on 3.12, 3.13 and 3.14 alike. **Installing Python 3.12 is not
required.** If you hit a runtime problem that looks version-specific, 3.12 is
the safest fallback — but try your current interpreter first.

**What actually broke your original script was not the Python version.**
`mediapipe` 1.x removed `mp.solutions` entirely:

```
>>> import mediapipe as mp; hasattr(mp, "solutions")
False
```

So `mp.solutions.face_mesh` cannot work on any current mediapipe, on any
Python. `alertride.py` uses the supported `FaceLandmarker` Tasks API instead.
The 478-point mesh has the same topology, so the EAR landmark indices are
unchanged — only the capture wrapper differs.

## Install

```
pip install -r requirements.txt
```

`face_landmarker.task` (3.76 MB) is already in this folder. If it goes
missing:

```
curl -L -o face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```

**Do not install `opencv-python-headless`.** It ships without GUI support, so
every `cv2.imshow()` call raises *"The function is not implemented"*. If you
already have it: `pip uninstall opencv-python-headless && pip install opencv-python`.

## Run, in this order

**1. Prove the logic — no board, no camera, 2 seconds.**
```
python tests/test_logic.py
```

**2. Prove the protocol — still no hardware.**
```
python hardware_test.py --sim
```
Walks every state through a software ESP32 that mirrors the firmware, and
proves the link-timeout failsafe fires. If this fails, the problem is the
code, not your wiring.

**3. Prove the board.** Close the Arduino Serial Monitor first.
```
python hardware_test.py
```
Finds the board by its USB chip ID (`VID_10C4/PID_EA60` for the CP210x), never
by a hardcoded `COMn` — that number follows the USB socket, and on this machine
`COM3`–`COM6` are Bluetooth serial, so a hardcoded `COM6` opens a Bluetooth
channel and hangs with no error.

Watch the board while it runs: green on `A`, red + beep + motor tap on `W`,
red blinking + steady tone + motor on `D`, silence on `S`.

**4. Run the real thing.**
```
python alertride.py
```
Opens the camera window and the dashboard. Runs camera-only if the board is
missing, and board-only with `--no-camera`, so either half can be worked on
alone.

**5. Calibrate.** Press `c` in the camera window. It measures your open and
shut EAR over three seconds each and sets the threshold between them. The
0.25 default is a starting point, not a correct value for your face, your
glasses or your lighting. `[` and `]` nudge it live.

**6. Test in this order:** eyes open, one normal blink, a deliberate 1-second
closure, a 3-second closure, then cover the camera entirely.

Every session writes `logs/session-*.csv` with timestamp, EAR, state and
threshold per frame. Record trials, false alarms, missed detections, lighting
and glasses on/off alongside it.

## Options

```
--port COM9         skip auto-detect
--sim               software ESP32, no hardware needed
--no-camera         board only, for testing the alert stages
--no-dashboard      skip the web dashboard
--camera-index 1    pick a different webcam
--threshold 0.22    starting EAR threshold
--warn-after 1.0    seconds of closure before WARNING
--drowsy-after 2.0  seconds of closure before DROWSY
```

## Files

| File | What it is |
| --- | --- |
| `core.py` | EAR maths, state machine, serial link. No camera or GUI imports, so it is unit-testable. |
| `alertride.py` | The application: capture, detect, drive the board, serve the dashboard. |
| `hardware_test.py` | Board check with no camera. **Run this before anything else.** |
| `esp32_sim.py` | Software ESP32 mirroring the firmware, for `--sim`. |
| `dashboard.html` | The live dashboard. Served by `alertride.py`, not opened directly. |
| `tests/test_logic.py` | 12 tests for the EAR and the state machine. No hardware. |
| `face_landmarker.task` | MediaPipe face mesh model, 3.76 MB. |

## Why it is a state machine and not an `if`

A normal blink is 100–400 ms and takes the EAR well below any sensible
threshold. Alerting on EAR alone would fire on every blink. Escalation is by
**duration of closure**: under 1 s is ignored, 1 s is WARNING, 2 s is DROWSY,
and opening your eyes resets the clock to zero.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| `PermissionError: could not open port` | The Arduino Serial Monitor is open. Windows gives the port to one process at a time. |
| No port found at all | CP210x driver missing. Device Manager → Ports; error code 28 on the device means no driver, so no COM port exists. |
| `cv2.imshow` "function is not implemented" | You have `opencv-python-headless`. Replace it with `opencv-python`. |
| `OSError: libEGL.so.1` | Linux only — `apt install libegl1 libgles2`. Windows ships EGL with the graphics driver. |
| Buzzer never sounds | Check `W12`, the common ground, first. A missing ground looks identical to a dead transistor. |
| Board reprints `AlertRide ready` mid-run | It is resetting. The 5 V rail is sagging under motor inrush — see "If you don't have a capacitor" in the build sheet. The dashboard logs this as an event. |
| Dashboard says "not receiving data" | `alertride.py` stopped. |

## Known gap

The EAR maths, the state machine, the serial protocol and the dashboard are
covered by automated tests. **Face detection on a real face is not** — it needs
a camera and a person, which is step 4 above. Everything on either side of that
link is verified; that link is yours to confirm.

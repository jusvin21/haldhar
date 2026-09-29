# AlertRide — project context

Anti-Sleep Driver Alert System. Handoff document: everything built, every
decision made and why, what is verified and what is not.

**Repo:** `jusvin21/haldhar` · branch `claude/alertride-hardware-build-rev-a-si7l7l`
**Build sheet (live):** https://claude.ai/artifact/CRAEZG4qP3kXVY2Rzwy79Q
**Hardware revision:** Rev B · **Date:** 2026-09-29

---

## 1. What this is

A prototype that watches the driver's eyes through a webcam, measures how long
they stay shut, and escalates through three alert stages on an ESP32: a green
status LED, a red alert LED, a buzzer and a 5 V vibration motor.

**Not a certified vehicle safety or medical device. Demonstrate stationary,
never in a moving vehicle.**

Signal chain:

```
webcam → MediaPipe face mesh → eye aspect ratio → state machine
       → serial (1 char) → ESP32 firmware → LEDs / buzzer / motor
                                          ↘ live dashboard (127.0.0.1:8000)
```

---

## 2. Repository layout

| Path | What it is |
| --- | --- |
| `hardware/BREADBOARD_MAP.md` | The wiring, as markdown. Every tie-point. |
| `hardware/alertride-breadboard.html` | Same thing as the published build sheet, with a drawn board. |
| `firmware/esp32_alert/esp32_alert.ino` | The Arduino sketch. |
| `software/core.py` | EAR maths, state machine, serial link. No camera or GUI imports — that is what makes it testable. |
| `software/alertride.py` | The application. Camera → detect → board → dashboard. |
| `software/hardware_test.py` | Board check, no camera. `--sim` needs no board either. |
| `software/esp32_sim.py` | Software ESP32 mirroring the firmware. |
| `software/dashboard.html` | Live dashboard. Served by `alertride.py`; do not open directly. |
| `software/tests/test_logic.py` | 12 tests. No hardware. |
| `software/face_landmarker.task` | MediaPipe model, 3.76 MB. |

Commits, oldest first:

```
f82825c  Add AlertRide Rev A breadboard map
a9f410b  Rev B: add the 5 V vibration motor stage
d56cb16  Make C1 optional and add a soft-start fallback
8a4d43e  Add the Python side: detector, board test, simulator, dashboard
```

---

## 3. Hardware — Rev B

**Board:** ESP32-WROOM-32 DevKit, 38-pin, seated **rows 62 → 44**, USB facing
row 63. Left header in column **b**, right header in column **i**.

**This board's pinout is mirrored** relative to the DevKitC V4 reference:
GND at (44, b) and 3V3 at (44, i). Every signal this circuit uses is therefore
on the **right** header, reached from column j.

### Pins in use (right header, column i)

| Row | Pin | Use |
| --- | --- | --- |
| 44 | 3V3 | W7 → buzzer + |
| 52 | GPIO25 | W5 → buzzer base resistor |
| 53 | GPIO26 | W8 → MOSFET gate resistor |
| 54 | GPIO27 | W3 → red LED |
| 55 | GPIO14 | W1 → green LED |
| 57 | GND | W12 → common ground |
| 62 | 5V / VIN | W13 → 5 V motor rail |

Row 56 (GPIO12) stays empty: a pull-up there at boot sets the flash to the
wrong voltage and the board will not start. Rows 59–62 on the *left* header
are flash pins — do not wire into them.

### Wire schedule (13 jumpers, no external supply)

| ID | From | To | Colour | Carries |
| --- | --- | --- | --- | --- |
| W1 | (55, j) | (3, j) | Green | GPIO14 → green LED |
| W2 | (8, j) | − rail @ 8 | Black | Green LED cathode → ground |
| W3 | (54, j) | (11, j) | Red | GPIO27 → red LED |
| W4 | (16, j) | − rail @ 16 | Black | Red LED cathode → ground |
| W5 | (52, j) | (19, j) | Yellow | GPIO25 → buzzer base |
| W6 | (23, j) | − rail @ 23 | Black | Q1 emitter → ground |
| W7 | (44, j) | (26, j) | Orange | 3V3 → buzzer + |
| W8 | (53, j) | (30, j) | Blue | GPIO26 → MOSFET gate |
| W9 | (37, j) | − rail @ 37 | Black | Gate pulldown → ground |
| W10 | (35, j) | − rail @ 35 | Black | Q2 source → ground |
| W11 | (40, j) | + rail @ 40 | Red | Motor + → 5 V rail |
| W12 | (57, j) | − rail @ 57 | Black | **ESP32 GND → common ground** |
| W13 | (62, j) | + rail @ 62 | Red | **ESP32 5V/VIN → 5 V rail** |

### Components

| Ref | Part | Lead A | Lead B | Note |
| --- | --- | --- | --- | --- |
| R1 | 220 Ω | (3, h) | (6, h) | red red brown gold |
| LED1 | Green | (6, f) anode | (8, f) cathode | long leg = anode |
| R2 | 220 Ω | (11, h) | (14, h) | red red brown gold |
| LED2 | Red | (14, f) anode | (16, f) cathode | |
| R3 | 1 kΩ | (19, h) | (22, h) | brown black red gold |
| Q1 | BC547 / 2N2222 | (21,i) (22,i) (23,i) | — | TO-92, flat face toward row 1 |
| BZ1 | Active buzzer | (21, g) − | (26, g) + | |
| R4 | 1 kΩ | (30, h) | (33, h) | gate series |
| R5 | 10 kΩ | (33, g) | (37, g) | gate pulldown |
| Q2 | IRLZ44N | (33,i) G, (34,i) D, (35,i) S | — | TO-220, tab toward row 63 |
| D1 | 1N4007 | (34, h) anode | (40, h) cathode | **band at row 40** |
| M1 | Vibration motor 5 V | (34, f) − | (40, f) + | |
| C1 | 100 µF **(optional)** | + rail @ 42 | − rail @ 42 | stripe leg is − |

### The four ways to get this wrong

1. **D1 backwards** shorts the 5 V rail to Q2's drain the instant W13 seats.
   Banded end at row 40. This is the one that kills the build immediately.
2. **Q1 backwards** → the buzzer sounds constantly regardless of command.
   BC547 reads C-B-E; 2N2222 in TO-92 reads E-B-C, the mirror. Base is row 22
   either way. If you use a 2N2222, move W6 to (21, j) and the buzzer negative
   to (23, g).
3. **Missing W12** → no shared ground, so Q1's base and Q2's gate see an
   undefined drive voltage. Looks identical to a dead transistor. Check this
   first when something does not switch.
4. **Non-logic-level MOSFET.** The `L` in IRLZ44N means its gate threshold is
   1–2 V, so a 3.3 V GPIO turns it fully on. An IRF540 needs ~10 V and would
   sit half-on, hot, with a weak motor.

---

## 4. The power decision (and the one risk it creates)

**The 5 V comes from the board's own `5V/VIN` pin at (62, i), not a battery
pack.** W13 carries it to the bottom + rail; W11 feeds the motor from there.

Rev A stripped the motor because two things could damage the ESP32: a 5 V node
that could back-feed a GPIO, and a supply whose ground floated relative to the
board. Sharing USB removes both — one supply, one ground. GPIO26 only drives
the MOSFET *gate*, which is isolated from drain and source, so no 5 V node ever
touches a GPIO.

**Current budget** (~300 mA worst case against USB's 500 mA):

| Load | Rail | Draw |
| --- | --- | --- |
| ESP32, Wi-Fi off | 3.3 V | ~45 mA |
| One LED + 220 Ω | 3.3 V | ~6 mA |
| Active buzzer | 3.3 V | ~30 mA |
| Motor running | 5 V | ~100 mA |
| Motor stall / inrush | 5 V | ~200 mA |

**The risk this creates is brownout, not damage.** Motor inrush sags the shared
5 V rail. Sag far enough and the ESP32 resets — the alert device reboots at the
exact moment it is supposed to be alerting.

**Symptom:** `AlertRide ready` reprinting mid-session. The dashboard logs it as
*"Board reset — check the 5 V rail"*.

**C1 (100 µF) is the fix but is NOT mandatory** — nothing is damaged without
it, and whether the reset happens at all depends on your motor and your cable.
Without a capacitor, in order of effort:

1. **Short thick USB cable, rear or motherboard port.** Never a hub or an
   unpowered front-panel header. Cable resistance is the biggest single lever
   and costs nothing.
2. **Set `MOTOR_SOFT_START = true`** in the sketch. Ramps the motor over ~25 ms
   with a software PWM instead of switching in one step. It deliberately avoids
   the LEDC peripheral, which `tone()` already uses for the buzzer, so it
   cannot break the buzzer stage. A workaround, not a substitute.
3. Shorten the motor leads, W11 and W13.
4. **Scavenge one.** Any electrolytic 47 µF–1000 µF rated ≥ 6.3 V. The small
   cylinders with a stripe. Dead router, phone charger, PC power supply, LED
   bulb base, old motherboard.

**If your motor stalls above ~350 mA**, USB cannot feed it alongside the ESP32
and you do need a separate pack — tie its ground to the − rail, never let its +
reach a GPIO. Measure with a multimeter in series on the 5 V lead, holding the
weight still.

---

## 5. Firmware

`firmware/esp32_alert/esp32_alert.ino` · Arduino IDE board **ESP32 Dev Module**,
upload 921600, flash 80 MHz, monitor 115200.

| Char | State | Green | Red | Buzzer | Motor |
| --- | --- | --- | --- | --- | --- |
| `A` | AWAKE | on | off | silent | off |
| `W` | WARNING | off | solid | 1800 Hz, 250 ms | 400 ms pulse |
| `D` | DROWSY | off | blinking 4 Hz | 2200 Hz continuous | latched on |
| `S` | STOPPED | off | off | silent | off |
| `?` | — | — | — | — | replies `AlertRide ready` |

**Why the motor behaves differently in the two stages.** `W` pulses; because
the host re-sends the current state once a second as a keepalive, WARNING reads
as a repeating tap. `D` latches. Tap versus continuous is a distinction you feel
without looking, which is the point of a haptic channel.

**Link-timeout failsafe.** Three seconds of host silence clears everything and
prints `LINK_LOST`. This matters more than it did in Rev A: an unattended motor
running flat out is worse than a stuck buzzer. The pulse ends on a `millis()`
deadline rather than `delay()`, because a 400 ms block in `loop()` would make
the failsafe itself unreliable.

**R5 is not decoration.** Between reset and `pinMode()` GPIO26 floats, and a
floating gate can hold enough charge to run the motor. R5 drains it.

**If `tone()` will not compile**, your ESP32 Arduino core is older than 3.x.
Update it in Boards Manager, or use `ledcWriteTone()`.

---

## 6. Python side

### You do not need Python 3.12

Checked against PyPI on 2026-09-29:

| Package | Windows wheel | Means |
| --- | --- | --- |
| `mediapipe` 1.0.1 | `py3-none-win_amd64` | no version restriction at all |
| `opencv-python` 5.0.0.93 | `cp37-abi3-win_amd64` | stable ABI, any CPython ≥ 3.7 |

Both install on 3.12, 3.13 and 3.14 alike. 3.12 is a fallback if something
version-specific bites, not a prerequisite.

### What actually broke the original script

```python
>>> import mediapipe as mp; hasattr(mp, "solutions")
False
```

**mediapipe 1.x removed `mp.solutions` entirely.** `mp.solutions.face_mesh`
is dead on every interpreter, at every Python version — downgrading would not
have helped. `alertride.py` uses the supported `FaceLandmarker` Tasks API. The
478-point mesh has the same topology, so the EAR landmark indices are
unchanged; only the capture wrapper differs.

### The other two original faults

- **`opencv-python-headless`** ships without GUI support, so every
  `cv2.imshow()` raises *"The function is not implemented"*. Use
  `opencv-python`.
- **A state-name mismatch silently disabled both alert stages.**
  `drowsiness_test.py` assigned `"BEEP"` / `"ALARM+VIBRATION"` but tested for
  `"WARNING"` / `"DROWSY"`, so neither branch ever matched and nothing said so.
  `core.py` now uses one set of names everywhere, and `send_state()` **raises**
  on an unknown state instead of returning quietly. That change caught a real
  bug in `hardware_test.py` during development — the same failure mode.

### Why it is a state machine and not an `if`

A normal blink is 100–400 ms and takes the EAR well below any sensible
threshold. Alerting on EAR alone would fire on every blink. Escalation is by
**duration of closure**: under 1 s ignored, 1 s → WARNING, 2 s → DROWSY,
eyes opening resets the clock to zero. The clock starts at the **first closed
frame**, not the last open one.

### Port detection

The board is found by USB chip ID (`VID_10C4/PID_EA60` for CP210x, plus CH340
and FTDI), never by a hardcoded `COMn`. Windows assigns that number per USB
socket, so it changes when the cable moves. **On this machine COM3–COM6 are
`Standard Serial over Bluetooth link`** — a hardcoded `COM6` opens a Bluetooth
channel and hangs with no error at all.

---

## 7. Run order

Steps 1 and 2 need **nothing plugged in**. If either fails, the problem is the
code, not the wiring.

```bash
cd software
pip install -r requirements.txt

python tests/test_logic.py      # 1. the logic          (~2 s, no hardware)
python hardware_test.py --sim   # 2. the protocol       (~12 s, no hardware)
python hardware_test.py         # 3. the real board     (close Serial Monitor)
python alertride.py             # 4. camera + dashboard at 127.0.0.1:8000
```

Then press **`c`** in the camera window to calibrate: it measures your open and
shut EAR over three seconds each and sets the threshold between them. 0.25 is a
starting point, not a correct value for your face, glasses or lighting. `[` and
`]` nudge it live, `q` quits.

Test in this order: eyes open, one normal blink, a deliberate 1-second closure,
a 3-second closure, then cover the camera entirely.

### Bring-up order for the board itself

1. Settle the COM port (section 9 below).
2. Seat the ESP32 alone, rows 44–62. Confirm GND at (44, b), 3V3 at (44, i).
   If reversed, stop — the board is not oriented as this map assumes.
3. Fit **W12** to the − rail. Ground before signals, always.
4. Upload the sketch. `AlertRide ready` must appear at 115200.
5. Green LED stage → send `A`.
6. Red LED stage → send `W`.
7. Buzzer stage → `W`, `D`, `S`.
8. Motor stage **with W13 left out** — nothing can move, which is the point.
   Check D1's band at row 40, C1's stripe on the − rail, Q2 reads G-D-S.
9. Fit **W13**. The motor must be dead still. If it runs the instant the wire
   seats, pull it and check R5 and Q2's orientation.
10. Test the motor: `W` pulse, `D` continuous, `S` stop.

Tape the motor to something — a loose one walks off the bench and drags the
wires out.

---

## 8. Verification status

**Verified** (automated, run 2026-09-29):

- 12/12 unit tests — EAR maths, scale invariance, divide-by-zero, blink
  rejection, escalation timing, closure-clock reset, no-face debounce,
  keepalive period, unknown-state raising.
- 5/5 protocol checks against a software ESP32 mirroring the firmware,
  including `LINK_LOST` actually firing.
- Full chain end to end: AWAKE → WARNING → DROWSY → NO_FACE → AWAKE, with
  blinks correctly ignored.
- `FaceLandmarker` loads the model and runs (~230 fps on the no-face path);
  returns `(None, None)` correctly when no face is present.
- Dashboard renders in light and dark, no console errors, no horizontal
  overflow at 390 px.

**NOT verified:**

- **Face detection on a real face.** Needs a camera and a person. Everything on
  either side of that link is tested; that link is yours to confirm.
- **Anything on real hardware.** The ESP32 is on a Windows PC; the work above
  was done in a Linux container with no USB, no COM port and no webcam.
- The firmware sketch has never been compiled by Arduino IDE. `esp32_sim.py`
  is a *model* of it, not proof of it. If you change one, change the other.

---

## 9. Open questions

1. **The COM port is unresolved.** Two contradictory readings are on record for
   the Windows machine — one says the CP210x driver is bound and the board holds
   a COM number, the other says Device Manager reports **error code 28** (no
   driver, therefore no port exists at all). Settle it in Device Manager →
   Ports (COM & LPT) before wiring. If code 28: install the Silicon Labs CP210x
   VCP driver, replug, re-check.

2. **Module header width was never measured.** 22.9 mm (0.9″) centre-to-centre
   → columns b and i as drawn. 25.4 mm (1.0″) → the module lands on a and j and
   covers every reachable hole, and you need a second breadboard butted against
   the first. Measure before committing.

3. **Motor stall current unmeasured.** The ~100 mA figure is typical for a small
   coin or bar ERM. Confirm against your part; above ~350 mA the USB-only power
   plan does not hold.

4. **Three silkscreen labels to confirm** on the right header before wiring:
   row 52 = GPIO25, row 55 = GPIO14, row 57 = GND. If any disagrees, stop.

---

## 10. Troubleshooting

| Symptom | Cause |
| --- | --- |
| `PermissionError: could not open port` | Arduino Serial Monitor is open. Windows gives the port to one process at a time. |
| No port found at all | CP210x driver missing. Error code 28 = no driver = no COM port. |
| `cv2.imshow` "function is not implemented" | You have `opencv-python-headless`. Replace with `opencv-python`. |
| `OSError: libEGL.so.1` | Linux only — `apt install libegl1 libgles2`. Windows ships EGL with the graphics driver. |
| Buzzer never sounds | Check W12, the common ground, first. |
| Buzzer sounds constantly | Q1 is in backwards. |
| Motor never moves | Check W13 and Q2's orientation. |
| Motor runs the moment power is applied | R5 missing, or Q2 in backwards. |
| `AlertRide ready` reprints mid-run | Board is resetting. 5 V rail sagging — section 4. |
| Dashboard says "not receiving data" | `alertride.py` stopped. |
| Alerts fire on every blink | Threshold or timing wrong. Press `c` to calibrate. |

---

*AlertRide Rev B — early-warning prototype. Not a certified vehicle safety or
medical device. Demonstrate stationary, never in a moving vehicle.*

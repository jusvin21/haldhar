# AlertRide Project Context for Claude

## User and event context

- User: Haldhar Singh Sethi
- Background: Engineering; located in Dadri, Uttar Pradesh, India.
- Current project: A hardware-focused drowsiness-alert prototype for MAITRON 2026, presented by ISTE MAIT Delhi.
- Query date context: 24 September 2026, India time.
- Submission deadline in the provided guidelines: 24 September 2026 at 11:59 PM IST.
- Grand Finale: 30 September 2026 at MAIT.

## Hackathon context

MAITRON 2026 is a student hackathon with Software and Hardware tracks. Teams have 2–4 members. Initial submission requires a maximum 10-slide PPT. The final round adds prototype evaluation. The guidelines list Open Spectrum as an option for a clearly stated problem of the team’s choice, so the drowsiness-alert project can be presented under Open Spectrum rather than forcing it into a listed SDG theme.

The project should be described honestly as an early-warning prototype, not a certified vehicle-safety or medical device. Demonstration must be done while stationary and never while driving.

## Finalized project

### Title

AlertRide: Real-Time Drowsiness Detection and Haptic Alert System

### Core problem

A driver or operator may experience prolonged eye closure or head nodding without immediate awareness. AlertRide uses a laptop webcam and computer vision to estimate eye closure. When prolonged closure is detected, it provides visual, audible, and haptic alerts through an ESP32.

### Current architecture

```text
Laptop webcam
      ↓
Python + OpenCV + MediaPipe
      ↓
Eye landmarks and Eye Aspect Ratio (EAR)
      ↓
Drowsiness state machine
      ↓ USB serial
ESP32-WROOM-32 DevKit V1
      ├── Green LED: awake
      ├── Red LED: warning/drowsy
      ├── Buzzer: audible alert
      └── Vibration motor: haptic alert
```

### Main states

- `AWAKE`: eyes open or normal blink.
- `WARNING`: eyes have remained below the EAR threshold for approximately 0.8 seconds.
- `DROWSY`: eyes have remained below the threshold for approximately 2 seconds.
- `NO_FACE`: no face is detected; camera status warning/safe stop.

The exact EAR threshold must be calibrated using the user’s own camera, lighting, face, and glasses. A starting value used so far is `EAR_THRESHOLD = 0.25`.

## Hardware selected

Recommended board:

- ESP32-WROOM-32 DevKit V1, 30-pin or 38-pin.
- Arduino IDE board selection: `ESP32 Dev Module`.
- USB data cable, not charge-only.

Current planned pin assignment:

| Function | ESP32 GPIO |
|---|---:|
| Green LED | GPIO14 |
| Red LED | GPIO27 |
| Buzzer control | GPIO25 |
| Vibration motor MOSFET gate | GPIO26 |
| Optional OLED SDA | GPIO21 |
| Optional OLED SCL | GPIO22 |
| Common ground | GND |

Expected components:

- ESP32-WROOM-32 DevKit V1.
- USB data cable.
- Solderless breadboard.
- Male-to-male and possibly male-to-female jumper wires.
- Active buzzer, 3.3 V or suitably rated.
- 3–5 V coin vibration motor.
- Red and green LEDs.
- 220 ohm resistors for LEDs.
- 1 kΩ resistors for transistor/MOSFET control.
- 10 kΩ gate pulldown resistor for MOSFET.
- Logic-level N-channel MOSFET, preferably IRLZ44N, for the motor.
- Optional NPN transistor such as 2N2222 or BC547 for buzzer driving.
- 1N4007 or 1N5819 flyback diode across the motor.
- Separate suitable 5 V motor supply or power bank.
- Optional OLED, MPU6050, battery, switch, enclosure, and perfboard.

### Motor wiring

For the IRLZ44N TO-220 package, verify the exact datasheet/pinout before powering. The commonly used front-facing arrangement with legs down is Gate–Drain–Source, but part variants must be checked.

```text
External +5 V → motor positive
motor negative → MOSFET Drain
MOSFET Source → common GND
ESP32 GPIO26 → 1 kΩ resistor → MOSFET Gate
10 kΩ resistor → Gate to GND
Diode striped side → motor positive / +5 V
Diode unstriped side → motor negative / MOSFET Drain
External supply GND → ESP32 GND
```

Never connect the motor directly to an ESP32 GPIO. Never apply 5 V directly to ESP32 GPIO pins.

### LED wiring

```text
GPIO14 → 220 Ω resistor → green LED long leg
green LED short leg → GND

GPIO27 → 220 Ω resistor → red LED long leg
red LED short leg → GND
```

### Buzzer driver wiring

For a transistor-driven buzzer:

```text
GPIO25 → 1 kΩ resistor → transistor base
transistor emitter → GND
transistor collector → buzzer negative
buzzer positive → suitable 3.3 V/5 V supply
```

The exact pinout of BC547 and 2N2222 depends on the part/package, so verify before wiring.

## Current software status

The user installed Python packages and has already successfully run:

- Webcam test using OpenCV.
- Face landmark test using MediaPipe.
- EAR calculation using MediaPipe facial landmarks.
- Drowsiness state logic using EAR and closure duration.
- Windows laptop sound alerts using `winsound`.
- On-screen simulated hardware status.

The user reported that the EAR code worked well and that the drowsiness code worked. They have now bought the hardware components and need to build and integrate the physical prototype.

## Python setup

Packages used:

```bash
python -m pip install opencv-python mediapipe numpy pyserial
```

The project folder was conceptually:

```text
AlertRide/
├── drowsiness_test.py
├── eye_test.py
├── camera_test.py
├── serial_test.py
└── esp32_alert.ino
```

## Python functions already discussed

At the top of the Python file, after imports:

```python
import cv2
import mediapipe as mp
import math
import time
import winsound


def trigger_warning():
    winsound.Beep(1200, 250)


def trigger_drowsy_alarm():
    for _ in range(3):
        winsound.Beep(1800, 300)


def get_hardware_status(state):
    if state == "AWAKE":
        return "GREEN LED ON | BUZZER OFF | MOTOR OFF"

    if state == "WARNING":
        return "RED LED ON | SHORT BEEP | MOTOR OFF"

    if state == "DROWSY":
        return "RED LED ON | BUZZER ON | MOTOR ON"

    if state == "NO_FACE":
        return "CAMERA CHECK | ALERT OFF"

    return "SYSTEM READY"
```

The software may need to be adapted if the user is not on Windows, because `winsound` is Windows-only.

## EAR code used

```python
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

EAR_THRESHOLD = 0.25
WARNING_TIME = 0.8
DROWSY_TIME = 2.0


def distance(point_a, point_b):
    return math.hypot(
        point_a.x - point_b.x,
        point_a.y - point_b.y
    )


def calculate_ear(landmarks, eye_indices):
    p1 = landmarks[eye_indices[0]]
    p2 = landmarks[eye_indices[1]]
    p3 = landmarks[eye_indices[2]]
    p4 = landmarks[eye_indices[3]]
    p5 = landmarks[eye_indices[4]]
    p6 = landmarks[eye_indices[5]]

    vertical_1 = distance(p2, p6)
    vertical_2 = distance(p3, p5)
    horizontal = distance(p1, p4)

    if horizontal == 0:
        return 0.0

    return (vertical_1 + vertical_2) / (2.0 * horizontal)
```

## Drowsiness state logic used

```python
eyes_closed_since = None
previous_state = "NO_FACE"

current_time = time.time()
state = "NO_FACE"
average_ear = 0.0
closed_duration = 0.0

if results.multi_face_landmarks:
    landmarks = results.multi_face_landmarks[0].landmark

    left_ear = calculate_ear(landmarks, LEFT_EYE)
    right_ear = calculate_ear(landmarks, RIGHT_EYE)
    average_ear = (left_ear + right_ear) / 2.0

    if average_ear < EAR_THRESHOLD:
        if eyes_closed_since is None:
            eyes_closed_since = current_time

        closed_duration = current_time - eyes_closed_since

        if closed_duration >= DROWSY_TIME:
            state = "DROWSY"
        elif closed_duration >= WARNING_TIME:
            state = "WARNING"
        else:
            state = "AWAKE"
    else:
        eyes_closed_since = None
        state = "AWAKE"
else:
    eyes_closed_since = None
    state = "NO_FACE"

hardware_status = get_hardware_status(state)
```

## On-screen display code

Place this inside the camera loop after state and hardware status have been calculated, before `cv2.imshow()`:

```python
if state == "AWAKE":
    color = (0, 255, 0)
elif state == "WARNING":
    color = (0, 165, 255)
elif state == "DROWSY":
    color = (0, 0, 255)
else:
    color = (255, 0, 255)

cv2.putText(
    frame,
    f"EAR: {average_ear:.3f}",
    (20, 40),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.8,
    (255, 255, 0),
    2
)

cv2.putText(
    frame,
    f"State: {state}",
    (20, 80),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.9,
    color,
    2
)

cv2.putText(
    frame,
    f"Closed: {closed_duration:.1f}s",
    (20, 120),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.8,
    color,
    2
)

cv2.putText(
    frame,
    hardware_status,
    (20, 200),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.55,
    color,
    2
)

cv2.imshow("AlertRide Drowsiness Test", frame)
```

## State-change sound block

Place this inside the `while True` camera loop after `state` is calculated and before display code:

```python
if state != previous_state:
    print(f"State changed: {previous_state} -> {state}")

    if state == "WARNING":
        trigger_warning()

    elif state == "DROWSY":
        trigger_drowsy_alarm()

    previous_state = state
```

It must not be placed inside `calculate_ear()`. It should be indented four spaces inside `while True`.

## ESP32 firmware already prepared

```cpp
const int GREEN_LED = 14;
const int RED_LED = 27;
const int BUZZER = 25;
const int MOTOR = 26;

void setup() {
  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  pinMode(BUZZER, OUTPUT);
  pinMode(MOTOR, OUTPUT);

  Serial.begin(115200);

  digitalWrite(GREEN_LED, LOW);
  digitalWrite(RED_LED, LOW);
  digitalWrite(MOTOR, LOW);
  noTone(BUZZER);

  Serial.println("AlertRide ready");
}

void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();

    if (command == 'A') {
      digitalWrite(GREEN_LED, HIGH);
      digitalWrite(RED_LED, LOW);
      digitalWrite(MOTOR, LOW);
      noTone(BUZZER);
      Serial.println("AWAKE");
    }

    else if (command == 'W') {
      digitalWrite(GREEN_LED, LOW);
      digitalWrite(RED_LED, HIGH);
      digitalWrite(MOTOR, LOW);
      tone(BUZZER, 1800, 250);
      Serial.println("WARNING");
    }

    else if (command == 'D') {
      digitalWrite(GREEN_LED, LOW);
      digitalWrite(RED_LED, HIGH);
      digitalWrite(MOTOR, HIGH);
      tone(BUZZER, 2200);
      Serial.println("DROWSY");
    }

    else if (command == 'S') {
      digitalWrite(GREEN_LED, LOW);
      digitalWrite(RED_LED, LOW);
      digitalWrite(MOTOR, LOW);
      noTone(BUZZER);
      Serial.println("STOPPED");
    }
  }
}
```

## Python-to-ESP32 integration code

Install PySerial if needed:

```bash
python -m pip install pyserial
```

Near the top of the Python script:

```python
import serial
import time
```

Before starting the camera:

```python
PORT = "COM6"       # Replace with the actual ESP32 COM port
BAUD_RATE = 115200

esp32 = serial.Serial(PORT, BAUD_RATE, timeout=1)
time.sleep(2)
```

Use this command function:

```python
last_command = None


def send_command(command):
    global last_command

    if command != last_command:
        esp32.write(command.encode())
        print(f"Sent command: {command}")
        last_command = command
```

Replace the sound-only state block with:

```python
if state != previous_state:
    print(f"State changed: {previous_state} -> {state}")

    if state == "AWAKE":
        send_command("A")
    elif state == "WARNING":
        send_command("W")
    elif state == "DROWSY":
        send_command("D")
    elif state == "NO_FACE":
        send_command("S")

    previous_state = state
```

At the end:

```python
camera.release()
cv2.destroyAllWindows()
esp32.close()
```

Close Arduino Serial Monitor before running Python because it may reserve the COM port.

## Recommended physical build order

1. Upload a serial test sketch to ESP32.
2. Confirm Arduino Serial Monitor at 115200 baud.
3. Connect and test green LED only.
4. Add and test red LED.
5. Add buzzer with its driver and test it.
6. Add motor/MOSFET/diode using separate motor supply.
7. Test complete ESP32 firmware with `A`, `W`, `D`, `S` commands.
8. Close Serial Monitor.
9. Connect Python to the ESP32 over the correct COM port.
10. Test eyes open, normal blink, warning, prolonged closure, and no-face behavior.
11. Mount the prototype and record results.

## Testing plan

| Test | Expected result |
|---|---|
| Eyes open | Green LED, no buzzer, motor off |
| Normal blink | No drowsy alarm |
| Eyes closed around 0.8 s | Warning/red LED and short beep |
| Eyes closed around 2 s | Red LED, buzzer, vibration motor |
| Eyes reopened | Return to awake state |
| Face removed | `NO_FACE`; alert stopped/safe camera warning |
| Serial disconnected | Python should report connection error safely |
| Motor starts | ESP32 should not reset |

Record the number of trials, false alarms, missed detections, lighting conditions, and whether glasses were used. Do not claim clinical or production accuracy from a small demo.

## Presentation context

Suggested 10-slide PPT:

1. Title, team members, Open Spectrum, and track.
2. Problem statement.
3. Target users/use case.
4. Proposed solution.
5. System block diagram.
6. EAR formula and drowsiness state algorithm.
7. Hardware circuit and component roles.
8. Working software/hardware prototype screenshots.
9. Feasibility, cost, limitations, and future improvements.
10. Expected impact and demo plan.

## Important constraints

- Test only while stationary; never test while driving.
- Do not call this a certified vehicle safety system.
- Do not claim it can guarantee accident prevention.
- The system is an early-warning prototype.
- Camera-based detection may fail with poor lighting, face occlusion, sunglasses, camera movement, and unusual head angles.
- The laptop performs computer vision; ESP32 controls alert outputs.
- Never connect a motor directly to an ESP32 GPIO.
- Never connect 5 V directly to ESP32 GPIO pins.
- Verify the exact pinout for every transistor/MOSFET before powering.

## How Claude should assist

When helping with this project:

1. Give step-by-step instructions for a beginner.
2. State exactly where code should be pasted.
3. Preserve the pin assignments unless there is a safety or hardware conflict.
4. If debugging, ask for the complete error message and relevant code section.
5. Prefer complete corrected code when multiple small edits would be confusing.
6. Distinguish Python code from Arduino C++ code.
7. Remind the user to close Serial Monitor before using PySerial.
8. Never recommend direct motor-to-GPIO wiring.
9. Keep hardware tests incremental.
10. Explain safety limits clearly.

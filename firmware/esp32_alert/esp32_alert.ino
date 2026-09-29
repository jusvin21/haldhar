// AlertRide alert driver - LED + buzzer + 5 V vibration motor (Rev B).
//
// Board:  ESP32 Dev Module, 115200 baud.
// Wiring: see hardware/BREADBOARD_MAP.md
//
// Serial protocol, one character per command:
//   A  AWAKE    green solid
//   W  WARNING  red solid, 250 ms beep, 400 ms motor pulse
//   D  DROWSY   red blinking 4 Hz, continuous tone, continuous motor
//   S  STOPPED  everything off
//   ?  replies "AlertRide ready"
//
// The host re-sends the current state once a second as a keepalive. Three
// seconds of silence trips the link-timeout failsafe and stops everything.

const int GREEN_LED = 14;   // row 55, col i
const int RED_LED   = 27;   // row 54, col i
const int BUZZER    = 25;   // row 52, col i
const int MOTOR     = 26;   // row 53, col i -> Q2 gate

const unsigned long LINK_TIMEOUT_MS = 3000;
const unsigned long MOTOR_PULSE_MS  = 400;

unsigned long lastCommandAt   = 0;
unsigned long motorPulseUntil = 0;   // 0 = not pulsing
char state = 'S';

void allOff() {
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(RED_LED, LOW);
  digitalWrite(MOTOR, LOW);
  motorPulseUntil = 0;
  noTone(BUZZER);
}

void applyState(char c) {
  state = c;

  if (c == 'A') {
    digitalWrite(GREEN_LED, HIGH);
    digitalWrite(RED_LED, LOW);
    digitalWrite(MOTOR, LOW);
    motorPulseUntil = 0;
    noTone(BUZZER);
    Serial.println("AWAKE");
  }
  else if (c == 'W') {
    digitalWrite(GREEN_LED, LOW);
    digitalWrite(RED_LED, HIGH);
    tone(BUZZER, 1800, 250);
    // Pulse, not latch. The 1 Hz keepalive re-triggers it, so WARNING
    // reads as a repeating tap; DROWSY below is the continuous one.
    digitalWrite(MOTOR, HIGH);
    motorPulseUntil = millis() + MOTOR_PULSE_MS;
    Serial.println("WARNING");
  }
  else if (c == 'D') {
    digitalWrite(GREEN_LED, LOW);
    tone(BUZZER, 2200);
    digitalWrite(MOTOR, HIGH);
    motorPulseUntil = 0;        // latched on until state changes
    Serial.println("DROWSY");
  }
  else if (c == 'S') {
    allOff();
    Serial.println("STOPPED");
  }
}

void setup() {
  // Drive the gate low before anything else. R5 handles the window
  // before this line runs; this holds it for the rest of the session.
  pinMode(MOTOR, OUTPUT);
  digitalWrite(MOTOR, LOW);

  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  pinMode(BUZZER, OUTPUT);
  allOff();

  Serial.begin(115200);
  delay(200);

  // Boot self-test: each output fires once, so a dead stage shows up
  // here rather than halfway through a demo. The motor goes last and
  // alone - if the board resets during it, the 5 V rail is sagging.
  digitalWrite(GREEN_LED, HIGH); delay(400); digitalWrite(GREEN_LED, LOW);
  digitalWrite(RED_LED, HIGH);   delay(400); digitalWrite(RED_LED, LOW);
  tone(BUZZER, 2000, 200);       delay(400);
  digitalWrite(MOTOR, HIGH);     delay(300); digitalWrite(MOTOR, LOW);

  lastCommandAt = millis();
  Serial.println("AlertRide ready");
}

void loop() {
  if (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') return;

    lastCommandAt = millis();

    if (c == '?') {
      Serial.println("AlertRide ready");
    } else if (c == 'A' || c == 'W' || c == 'D' || c == 'S') {
      applyState(c);
    }
    return;
  }

  // End a WARNING pulse without blocking the serial read above.
  if (motorPulseUntil != 0 && millis() >= motorPulseUntil) {
    digitalWrite(MOTOR, LOW);
    motorPulseUntil = 0;
  }

  // Red blinks in DROWSY, stays solid in WARNING. Second escalation
  // channel alongside the motor, and the one a camera can see.
  if (state == 'D') {
    digitalWrite(RED_LED, (millis() / 120) % 2 ? HIGH : LOW);
  }

  // Failsafe. A latched motor is worse than a latched buzzer: it can
  // run flat out unattended. Silence from the host stops everything.
  if ((state == 'W' || state == 'D') && millis() - lastCommandAt > LINK_TIMEOUT_MS) {
    allOff();
    state = 'S';
    Serial.println("LINK_LOST");
  }
}

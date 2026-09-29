# AlertRide — Breadboard Map (Rev B)

Anti-Sleep Driver Alert System · ESP32-WROOM-32 DevKit (38-pin)
Two LEDs · buzzer · 5 V vibration motor · USB powered, no external pack

---

## 0. Module placement — read this first

**The ESP32-WROOM module occupies rows 62 down to 44**, USB connector
facing the row-63 end of the board and overhanging it so the cable clears
everything.

- That span is **19 rows**, which is exactly the pin count per side on a
  38-pin DevKit: **one pin per row**, each isolated from its neighbour by
  the centre gap.
- **Left header → column b**, rows 44–62. Reached from column a.
- **Right header → column i**, rows 44–62. Reached from column j.
  The working side: 3V3 at 44, GPIO25/26/27/14 at 52–55, GND at 57,
  and **5V/VIN at 62** — where the motor rail comes from.
- Columns **c d e f g h** in rows 44–62 sit *underneath* the module and
  are unusable.

### Measure before you commit
Header-to-header, centre-to-centre across the two pin rows:

| Width | Result |
| --- | --- |
| 22.9 mm (0.9") | Lands on **b** and **i**; a and j stay free. **This is the layout drawn here.** |
| 25.4 mm (1.0") | Lands on **a** and **j** and covers every reachable hole. You need a second breadboard butted against the first, jumpered across. |

---

## 1. Serial port — UNRESOLVED, verify before wiring

Two conflicting readings exist for this machine. Settle it in Device
Manager under **Ports (COM & LPT)** before you open Arduino IDE.

- **If the CP210x VCP driver is installed:** the board enumerates as
  *Silicon Labs CP210x USB to UART Bridge*, VID_10C4 / PID_EA60, and gets
  a COM number.
- **If Device Manager shows error code 28** on that device: the driver is
  **not** installed and **no COM port exists yet**. Install the Silicon
  Labs CP210x VCP driver, replug, then re-check.

Three things that hold either way:

1. **The COM number is not permanent.** Windows assigns it per USB
   socket. Move the cable, it changes. Match on VID/PID in software, never
   a hardcoded string.
2. **COM3–COM6 on this machine are Bluetooth**, not the board
   (*Standard Serial over Bluetooth link*). A `PORT = "COM6"` line opens a
   Bluetooth channel and hangs with no error.
3. **One process owns the port.** Close the Arduino Serial Monitor before
   running Python, or PySerial raises `PermissionError`.

---

## 2. Pin-to-row reference

Read off the silkscreen of *this* board: **GND at (44, b)** and
**3V3 at (44, i)**. That is the mirror of the DevKitC V4 reference order,
so every signal this circuit uses sits on the **right** header.

### Left header · column b

| Row | Pin | Use |
| --- | --- | --- |
| 44 | GND | spare ground |
| 45 | GPIO23 | free |
| 46 | GPIO22 | OLED SCL option |
| 47 | GPIO1 · TX0 | USB serial — keep clear |
| 48 | GPIO3 · RX0 | USB serial — keep clear |
| 49 | GPIO21 | OLED SDA option |
| 50 | GND | spare ground |
| 51 | GPIO19 | free |
| 52 | GPIO18 | free |
| 53 | GPIO5 | free |
| 54 | GPIO17 · TX2 | free |
| 55 | GPIO16 · RX2 | free |
| 56 | GPIO4 | free |
| 57 | GPIO0 | boot strap — leave empty |
| 58 | GPIO2 | strapping — leave empty |
| 59 | GPIO15 | strapping — leave empty |
| 60 | GPIO8 · SD1 | flash — do not use |
| 61 | GPIO7 · SD0 | flash — do not use |
| 62 | GPIO6 · CLK | flash — do not use |

### Right header · column i — the working side

| Row | Pin | Use |
| --- | --- | --- |
| 44 | 3V3 | **W7** buzzer + |
| 45 | EN | reset |
| 46 | GPIO36 · VP | free, input only |
| 47 | GPIO39 · VN | free, input only |
| 48 | GPIO34 | free, input only |
| 49 | GPIO35 | free, input only |
| 50 | GPIO32 | free |
| 51 | GPIO33 | free |
| 52 | GPIO25 | **W5** buzzer |
| 53 | GPIO26 | **W8** motor gate |
| 54 | GPIO27 | **W3** red LED |
| 55 | GPIO14 | **W1** green LED |
| 56 | GPIO12 | strapping — **leave empty** |
| 57 | GND | **W12** common ground |
| 58 | GPIO13 | free |
| 59 | GPIO9 · SD2 | flash — do not use |
| 60 | GPIO10 · SD3 | flash — do not use |
| 61 | GPIO11 · CMD | flash — do not use |
| 62 | 5V · VIN | **W13** motor supply |

**Confirm three labels before wiring anything:** right header row 52 should
read GPIO25, row 55 GPIO14, row 57 GND. If any disagrees, stop — wiring
into rows 59–62 on either side reaches the flash pins.

**Why these four GPIOs:** 14, 25, 26 and 27 have no boot-time strapping
duty and no flash connection, so a load on any of them cannot stop the
board from starting. Row 56 (GPIO12) stays empty even though it sits in
the middle of the cluster: a pull-up there at boot sets the flash to the
wrong voltage and the board will not come up.

**Row 62 on the right header is `5V/VIN`, not a GPIO** — drawing current
out of it is what it is for. Do not confuse it with row 62 on the *left*
header, which is the flash clock.

---

## 3. Circuit zones

Four output stages in rows 3–40, all sharing one ground rail. Everything
sits in columns f–j because that is the side the signal pins face. Three
run at 3.3 V; the motor runs at 5 V behind a MOSFET, and no 5 V node ever
touches a GPIO.

### Green LED — AWAKE · GPIO14
| Item | Tie-points |
| --- | --- |
| W1 jumper | (55, j) → (3, j) |
| R1 220 Ω | (3, h) → (6, h) |
| LED1 anode (long leg) | (6, f) |
| LED1 cathode (flat rim) | (8, f) |
| W2 jumper | (8, j) → − rail @ 8 |

### Red LED — WARNING / DROWSY · GPIO27
| Item | Tie-points |
| --- | --- |
| W3 jumper | (54, j) → (11, j) |
| R2 220 Ω | (11, h) → (14, h) |
| LED2 anode | (14, f) |
| LED2 cathode | (16, f) |
| W4 jumper | (16, j) → − rail @ 16 |

### Buzzer — NPN low-side switch · GPIO25
| Item | Tie-points |
| --- | --- |
| W5 jumper | (52, j) → (19, j) |
| R3 1 kΩ (base) | (19, h) → (22, h) |
| Q1 legs | (21, i) (22, i) (23, i) |
| W6 jumper | (23, j) → − rail @ 23 |
| BZ1 − (collector row) | (21, g) |
| BZ1 + | (26, g) |
| W7 jumper | (44, j) 3V3 → (26, j) |

### Motor — MOSFET low side · GPIO26
| Item | Tie-points |
| --- | --- |
| W8 jumper | (53, j) → (30, j) |
| R4 1 kΩ (gate series) | (30, h) → (33, h) |
| R5 10 kΩ (gate pulldown) | (33, g) → (37, g) |
| Q2 gate | (33, i) |
| Q2 drain | (34, i) |
| Q2 source | (35, i) |
| W9 jumper | (37, j) → − rail @ 37 |
| W10 jumper | (35, j) → − rail @ 35 |
| D1 anode | (34, h) |
| D1 cathode (**banded end**) | (40, h) |
| M1 motor − | (34, f) |
| M1 motor + | (40, f) |
| W11 jumper | (40, j) → + rail @ 40 |
| C1 100 µF | + rail @ 42 / − rail @ 42 |
| W13 jumper | (62, j) 5V → + rail @ 62 |

---

## 4. Wire schedule

Thirteen jumpers. No external supply, no battery pack — the bottom + rail
is 5 V tapped from the board's own VIN pin.
Colours are convention, not electrical requirement — but following them
makes a fault obvious at a glance.

| ID | From | To | Colour | Carries |
| --- | --- | --- | --- | --- |
| W1 | (55, j) | (3, j) | Green | GPIO14 → green LED stage |
| W2 | (8, j) | − rail @ 8 | Black | Green LED cathode → ground |
| W3 | (54, j) | (11, j) | Red | GPIO27 → red LED stage |
| W4 | (16, j) | − rail @ 16 | Black | Red LED cathode → ground |
| W5 | (52, j) | (19, j) | Yellow | GPIO25 → buzzer base resistor |
| W6 | (23, j) | − rail @ 23 | Black | Q1 emitter → ground |
| W7 | (44, j) | (26, j) | Orange | 3V3 → buzzer positive |
| W8 | (53, j) | (30, j) | Blue | GPIO26 → MOSFET gate resistor |
| W9 | (37, j) | − rail @ 37 | Black | R5 gate pulldown → ground |
| W10 | (35, j) | − rail @ 35 | Black | Q2 source → ground |
| W11 | (40, j) | + rail @ 40 | Red | Motor + → 5 V rail |
| W12 | (57, j) | − rail @ 57 | Black | **ESP32 GND → common ground** |
| W13 | (62, j) | + rail @ 62 | Red | **ESP32 5V/VIN → 5 V rail** |

**Fit W12 before any signal wire.** Q1 compares the GPIO voltage against
*its own* emitter, and Q2 against its own source. Without a shared ground
either sees an undefined drive voltage and latches on or never turns on.

**Fit W13 last**, after the motor stage is built and checked. It is the
only wire that puts 5 V on the board; until it goes in, a mistake in the
motor stage cannot do anything.

Both rails above column a stay empty. Only the bottom pair is used —
− for ground, + for the 5 V motor rail.

---

## 5. Components

Resistor bands given 4-band with gold tolerance ring, read from the
crowded end.

| Ref | Part | Lead A | Lead B | Identify by |
| --- | --- | --- | --- | --- |
| R1 | 220 Ω | (3, h) | (6, h) | red red brown gold |
| LED1 | Green LED | (6, f) anode | (8, f) cathode | Long leg = anode; flat rim = cathode |
| R2 | 220 Ω | (11, h) | (14, h) | red red brown gold |
| LED2 | Red LED | (14, f) anode | (16, f) cathode | Long leg = anode |
| R3 | 1 kΩ | (19, h) | (22, h) | brown black red gold |
| Q1 | BC547 / 2N2222 | (21, i) (22, i) (23, i) | — | TO-92, flat face toward row 1 |
| BZ1 | Active buzzer | (21, g) − | (26, g) + | Longer pin / + mark = positive |
| R4 | 1 kΩ | (30, h) | (33, h) | brown black red gold |
| R5 | 10 kΩ | (33, g) | (37, g) | brown black orange gold |
| Q2 | IRLZ44N MOSFET | (33,i) (34,i) (35,i) | — | TO-220, tab toward row 63 — G D S |
| D1 | 1N4007 flyback | (34, h) anode | (40, h) cathode | **Banded end at row 40**, the + side |
| M1 | Vibration motor 5 V | (34, f) − | (40, f) + | Usually red = +, black = − |
| C1 | 100 µF electrolytic | + rail @ 42 | − rail @ 42 | **Stripe leg is −** — backwards it can vent |

### Q1 leg order flips between the two parts you may have
Hold it flat-face toward you, legs down, read left to right:

- **BC547 → C B E.** Row 21 = collector, 22 = base, **23 = emitter**.
  *This is what the map assumes.*
- **2N2222 (TO-92) → E B C**, the reverse. If you use this part, move W6
  to (21, j) and the buzzer negative to (23, g).

Base stays at row 22 either way. Confirm against the datasheet for your
exact marking before power.

**If the buzzer never sounds at all, check W12 first.** A missing ground
is by far the most common cause and looks identical to a dead transistor.
If it sounds constantly the moment power is applied regardless of what you
send, Q1 is in backwards.

### Q2 — IRLZ44N, TO-220

Printed face toward you, metal tab pointing away toward row 63, read left
to right: **G D S**. So (33, i) = gate, (34, i) = drain, (35, i) = source.
**The tab is electrically the drain** — do not let it touch anything.

**Why the IRLZ44N and not any MOSFET.** Its gate threshold is 1–2 V, so a
3.3 V GPIO turns it fully on. A standard IRF540 needs ~10 V and would sit
half-on, heating up and running the motor weakly. Look for the `L` in the
part number; it means logic-level.

**D1 backwards is the one mistake that kills the build instantly.**
Reversed, it shorts the 5 V rail to the drain the moment W13 goes in. The
banded (cathode) end goes to row 40, the + side. Check it twice.

**R5 is not decoration.** Between reset and `pinMode()` GPIO26 floats, and
a floating gate can hold enough charge to run the motor. R5 drains it, so
the motor is off from the instant power is applied.

---

## 6. Powering the 5 V motor

The motor needs 5 V; the ESP32 needs 3.3 V logic. Rev B resolves that
without a second supply, which is what kept Rev A safe.

**The 5 V comes from the board, not a pack.** Pin `5V/VIN` at (62, i) is
USB 5 V passed through the DevKit. W13 carries it to the bottom + rail,
and W11 feeds the motor from there.

**Why that matters.** A battery pack reintroduces both hazards Rev A
removed: a 5 V node that can back-feed a GPIO, and a supply whose ground
floats relative to the board. Sharing USB keeps one supply and one ground,
so neither can happen.

**No 5 V ever reaches a GPIO.** GPIO26 only drives the MOSFET *gate*,
which is isolated from drain and source. The 5 V lives entirely on the +
rail, the motor, and Q2's drain.

### Brownout is the real risk now, not damage

Motor inrush sags the 5 V rail. Sag far enough and the ESP32 resets — the
alert device reboots at the exact moment it is supposed to be alerting,
and nothing on screen tells you it happened.

**C1, 100 µF across the bottom rails at position 42, is the fix.** It
supplies the inrush locally so the rail does not dip. Not optional; Rev A
had no bulk capacitance because it had no motor. Stripe leg (−) to the
− rail.

**Symptom to watch for:** if the board prints `AlertRide ready` again in
the middle of a DROWSY test, that is a reset, not a glitch. Check C1 is
seated and its polarity is right.

### Current budget

| Load | Rail | Draw | Note |
| --- | --- | --- | --- |
| ESP32, Wi-Fi off | 3.3 V | ~45 mA | Regulated on the DevKit from the same USB 5 V |
| One LED + its 220 Ω | 3.3 V | ~6 mA | Only one LED is ever lit at a time |
| Active buzzer | 3.3 V | ~30 mA | Through Q1 |
| Motor, running | 5 V | ~100 mA | Typical small ERM — **confirm against your part** |
| Motor, stall / inrush | 5 V | ~200 mA | Brief; this is what C1 absorbs |
| **Worst case, all on** | — | **~300 mA** | Against a USB 2.0 port's 500 mA |

**Measure your motor's stall current before you trust this table.** The
100 mA figure is typical for a small coin or bar ERM vibration motor. If
yours is a geared DC motor, or anything drawing **more than about 350 mA
stalled**, USB cannot feed it alongside the ESP32 and you do need a
separate pack — in which case tie its ground to the − rail and never let
its + reach a GPIO.

To measure: put a multimeter in series on the 5 V lead, run the motor,
then hold the shaft or weight still and read the peak.

---

## 7. Firmware

Arduino IDE board: **ESP32 Dev Module**. Upload speed 921600, flash
frequency 80 MHz, monitor 115200.
Sketch: [`firmware/esp32_alert/esp32_alert.ino`](../firmware/esp32_alert/esp32_alert.ino).

Serial protocol, one character per command:

| Char | State | Green | Red | Buzzer |
| --- | --- | --- | --- | --- |
| `A` | AWAKE | on | off | silent |
| `W` | WARNING | off | solid | 1800 Hz, 250 ms |
| `D` | DROWSY | off | **blinking ~4 Hz** | 2200 Hz continuous |
| `S` | STOPPED | off | off | silent |
| `?` | — | — | — | replies `AlertRide ready` |

Motor behaviour, the fourth column the table above leaves out:

| Char | Motor |
| --- | --- |
| `A` | off |
| `W` | 400 ms pulse, re-triggered by each 1 Hz keepalive → repeating tap |
| `D` | latched on until the state changes |
| `S` | off |

**Tap versus continuous is the point.** WARNING pulses the motor; DROWSY
latches it. That is a distinction you feel without looking, which is what
a haptic channel is for in a driver alert.

**DROWSY also blinks the red LED.** Rev A added that to replace the
missing motor; it stays, because it is the channel a demo camera can
record. Solid red = WARNING, 4 Hz blink = DROWSY.

**Link-timeout failsafe, and it matters more now.** `D` latches both the
tone and the motor. If the host crashes mid-alert, nothing sends `S` — and
an unattended motor running flat out is a worse failure than a stuck
buzzer. Three seconds of host silence clears everything and prints
`LINK_LOST`. Because the host only transmits on a state *change*, a long
steady DROWSY would trip that too, so the host re-sends the current state
once a second as a keepalive.

**Non-blocking on purpose.** The motor pulse ends via a `millis()`
deadline rather than `delay()`, so a 400 ms buzz never blocks the serial
read — a `delay()` there would make the failsafe itself unreliable.

**If `tone()` will not compile**, your ESP32 Arduino core is older than
3.x, where `tone()` was added. Update the core in Boards Manager, or drive
the buzzer with `ledcWriteTone()`. Nothing else is core-version sensitive.

**Boot self-test:** each output fires once at startup, so a dead stage
shows up then rather than halfway through a demo.

---

## 8. Bring-up order

Each step adds one stage and proves it before the next goes in. If
something fails, you know what caused it.

1. **Driver and port.** Resolve section 1 first. Select the board's real
   COM port and ESP32 Dev Module in Arduino IDE.
2. **Seat the ESP32 alone**, rows 44–62, columns b and i, USB facing row
   63. Confirm GND at (44, b) and 3V3 at (44, i). If they are the other
   way round, the board is not oriented as this map assumes — stop.
3. **Fit W12**, (57, j) → bottom − rail. Ground before signals, always.
4. **Upload the sketch** with nothing else connected. The self-test does
   nothing visible yet, but `AlertRide ready` must appear at 115200.
5. **Green LED stage** — R1, LED1, W1, W2. Send `A`. Green lights. If not,
   check the LED is not backwards before anything else.
6. **Red LED stage** — R2, LED2, W3, W4. Send `W`. Green drops, red lights.
7. **Buzzer stage** — R3, Q1, BZ1, W5, W6, W7. `W` = short beep, `D` =
   steady tone, `S` = silence. Constant buzz regardless of command means
   Q1 is in backwards.
8. **Motor stage, dry** — R4, R5, Q2, D1, M1, W8, W9, W10, W11, C1.
   **Leave W13 out.** With no 5 V on the rail nothing can move yet, which
   is the point: check D1's band is at row 40, C1's stripe is on the −
   rail, and Q2 reads G-D-S into rows 33-34-35.
9. **Fit W13** from (62, j) to the + rail. This is the moment 5 V enters
   the board. The motor must be still — if it runs the instant you seat
   this wire, pull it out and check R5 and Q2's orientation.
10. **Test the motor** — `W` for a pulse, `D` for continuous, `S` to stop.
    If the board reprints `AlertRide ready` when the motor starts, the
    5 V rail is browning out: check C1, then measure stall current.
11. **Close the Serial Monitor**, run the hardware test script. It drives
    every state and prints the replies, including the LINK_LOST failsafe.
    Whole hardware check in one command, no camera.
12. **Run the detection script.** Test in order: eyes open, one normal
    blink, a deliberate 1-second closure, a 3-second closure, then cover
    the camera entirely.
13. **Calibrate the threshold.** Watch the on-screen EAR open and shut,
    set the threshold midway. The 0.25 default is a starting point, not a
    correct value for your face, glasses or lighting.
14. **Log the run** — trials, false alarms, missed detections, lighting,
    glasses on or off. Stationary only.
15. **Tape the motor down.** A loose vibration motor walks off the bench
    and drags the breadboard wires out with it.

---

AlertRide — early-warning prototype. **Not a certified vehicle safety or
medical device. Demonstrate stationary, never in a moving vehicle.** Rev B

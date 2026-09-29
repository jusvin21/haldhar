# AlertRide — Breadboard Map (Rev A)

Anti-Sleep Driver Alert System · ESP32-WROOM-32 DevKit (38-pin)
LED + buzzer build · no vibration motor · 3.3 V off USB only

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
| 53 | GPIO26 | reserved for motor — leave unwired |
| 54 | GPIO27 | **W3** red LED |
| 55 | GPIO14 | **W1** green LED |
| 56 | GPIO12 | strapping — **leave empty** |
| 57 | GND | **W12** common ground |
| 58 | GPIO13 | free |
| 59 | GPIO9 · SD2 | flash — do not use |
| 60 | GPIO10 · SD3 | flash — do not use |
| 61 | GPIO11 · CMD | flash — do not use |
| 62 | 5V · VIN | unused here |

**Confirm three labels before wiring anything:** right header row 52 should
read GPIO25, row 55 GPIO14, row 57 GND. If any disagrees, stop — wiring
into rows 59–62 on either side reaches the flash pins.

**Why these four GPIOs:** 14, 25, 26 and 27 have no boot-time strapping
duty and no flash connection, so a load on any of them cannot stop the
board from starting. Row 56 (GPIO12) stays empty even though it sits in
the middle of the cluster: a pull-up there at boot sets the flash to the
wrong voltage and the board will not come up.

---

## 3. Circuit zones

Four output stages in rows 3–40, all sharing one ground rail. Everything
sits in columns f–j because that is the side the signal pins face.

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

### Motor — NOT in this build · GPIO26
Rows 30–40 stay completely empty. The + rail is unused; there is no
external supply. See section 6 for what comes out and where it goes back.

---

## 4. Wire schedule

Seven jumpers. No external supply, no battery pack, no + rail.
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
| W12 | (57, j) | − rail @ 57 | Black | **ESP32 GND → common ground** |

**Fit W12 before any signal wire.** Q1 compares the GPIO voltage against
*its own* emitter. Without a shared ground the base sees an undefined
voltage and the buzzer either never sounds or never stops.

Both rails above column a stay empty, and so does the bottom + rail. Only
the bottom − rail is used.

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

### Q1 leg order flips between the two parts you may have
Hold it flat-face toward you, legs down, read left to right:

- **BC547 → C B E.** Row 21 = collector, 22 = base, **23 = emitter**.
  *This is what the map assumes.*
- **2N2222 (TO-92) → E B C**, the reverse. If you use this part, move W6
  to (21, j) and the buzzer negative to (23, g).

Base stays at row 22 either way. Confirm against the datasheet for your
exact marking before power.

**Q1 is the only active device on the board.** If the buzzer sounds
constantly the moment power is applied regardless of what you send, the
transistor is in backwards — pull it, rotate it, retry before suspecting
anything else. If it never sounds at all, **check W12 first**; a missing
ground is by far the most common cause and looks identical to a dead
transistor.

---

## 6. What comes off the board

Everything below is removed for this build. Rows 30–40 end up empty, and
so does the external supply. **Keep all of it** — these coordinates are
what you put back when a new motor arrives.

| Pull | What it is | From | Why |
| --- | --- | --- | --- |
| W8 | Jumper, blue | (53, j) → (30, j) | Fed GPIO26 to the gate |
| R4 | 1 kΩ | (30, h) → (33, h) | Gate series resistor |
| R5 | 10 kΩ | (33, g) → (37, g) | Gate pulldown |
| Q2 | IRLZ44N MOSFET | (33, i) (34, i) (35, i) | Nothing left to switch |
| D1 | Flyback diode | (34, h) → (40, h) | Only needed across an inductive load |
| W9 | Jumper, black | (37, j) → − rail | Pulldown ground |
| W10 | Jumper, black | (35, j) → − rail | MOSFET source ground |
| W11 | Jumper, red | (40, j) → + rail | Motor supply feed |
| M1 | Vibration motor | (34, f) (40, f) | Lead is broken |
| P1 | Pack +5 V lead | + rail @ 63 | No external supply at all now |
| P2 | Pack GND lead | − rail @ 62 | Nothing left to share a ground with |

**This build is safer than the full one, not just smaller.** The two ways
to damage an ESP32 here were back-feeding 5 V into a GPIO and letting the
motor supply float relative to the board. Both leave with the motor.
Everything remaining runs at 3.3 V off USB.

**Leave GPIO26 unwired at (53, j).** The firmware no longer drives it, and
a clear row means the motor stage drops straight back in with no rework.

---

## 7. Firmware

Arduino IDE board: **ESP32 Dev Module**. Upload speed 921600, flash
frequency 80 MHz, monitor 115200. Sketch: `firmware/esp32_alert/esp32_alert.ino`.

Serial protocol, one character per command:

| Char | State | Green | Red | Buzzer |
| --- | --- | --- | --- | --- |
| `A` | AWAKE | on | off | silent |
| `W` | WARNING | off | solid | 1800 Hz, 250 ms |
| `D` | DROWSY | off | **blinking ~4 Hz** | 2200 Hz continuous |
| `S` | STOPPED | off | off | silent |
| `?` | — | — | — | replies `AlertRide ready` |

**DROWSY blinks the red LED** because the motor was what separated
"warning" from "wake up". With it gone, solid red plus a tone looks
identical in both states, so escalation moves to the blink.

**Link-timeout failsafe:** `D` holds a continuous tone. If the host
crashes mid-alert, nothing sends `S` and the buzzer runs until you pull
the cable. Three seconds of silence from the host resets to STOPPED and
prints `LINK_LOST`. Because the host only transmits on a state *change*, a
long steady DROWSY would trip that too — so the host re-sends the current
state once a second as a keepalive.

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
8. **Close the Serial Monitor**, run the hardware test script. It drives
   every state and prints the replies, including the LINK_LOST failsafe.
   Whole hardware check in one command, no camera.
9. **Run the detection script.** Test in order: eyes open, one normal
   blink, a deliberate 1-second closure, a 3-second closure, then cover
   the camera entirely.
10. **Calibrate the threshold.** Watch the on-screen EAR open and shut,
    set the threshold midway. The 0.25 default is a starting point, not a
    correct value for your face, glasses or lighting.
11. **Log the run** — trials, false alarms, missed detections, lighting,
    glasses on or off. Stationary only.

---

AlertRide — early-warning prototype. **Not a certified vehicle safety or
medical device. Demonstrate stationary, never in a moving vehicle.** Rev A

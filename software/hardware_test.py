"""Run this first. Checks the board and every output stage, no camera.

    python hardware_test.py            # find the board by chip ID
    python hardware_test.py --port COM9
    python hardware_test.py --sim      # no board needed, exercises the protocol

Close the Arduino Serial Monitor before running: Windows gives the port to one
process at a time, and with the monitor open pyserial raises PermissionError.
"""
from __future__ import annotations

import argparse
import sys
import time

from core import AWAKE, DROWSY, NO_FACE, WARNING, BoardLink

RESET = "\033[0m"
DIM = "\033[2m"
OK = "\033[32m"
BAD = "\033[31m"
WARN = "\033[33m"


def say(tag, msg, colour=""):
    print(f"{colour}{tag:<7}{RESET} {msg}", flush=True)


def drain(link, seconds, label=""):
    """Read replies for a while, printing them as they arrive."""
    seen = []
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        for line in link.read_replies():
            seen.append(line)
            print(f"        {DIM}board:{RESET} {line}", flush=True)
        time.sleep(0.02)
    return seen


def step(link, cmd, state, hold, expect, prompt):
    print()
    say("SEND", f"{cmd}   {prompt}")
    link.send_state(state, force=True)
    seen = drain(link, hold)
    if expect in seen:
        say("OK", f"board replied {expect}", OK)
        return True
    say("FAIL", f"expected {expect}, got {seen or 'nothing'}", BAD)
    return False


def main():
    ap = argparse.ArgumentParser(description="AlertRide hardware check")
    ap.add_argument("--port", help="serial port, e.g. COM9 (default: auto-detect)")
    ap.add_argument("--sim", action="store_true",
                    help="use the software ESP32 instead of real hardware")
    args = ap.parse_args()

    print("AlertRide hardware check")
    print("=" * 46)

    link = BoardLink(port=args.port)
    if args.sim:
        link.connect_simulated()
        say("PORT", "simulated board (no hardware in the loop)", WARN)
    elif not link.connect():
        say("FAIL", link.error, BAD)
        print("\nThings to check, in order:")
        print("  1. Is the CP210x driver installed? Device Manager > Ports.")
        print("     Error code 28 on the device means no driver, so no port.")
        print("  2. Is the Arduino Serial Monitor still open? Close it.")
        print("  3. COM3-COM6 on this machine are Bluetooth, not the board.")
        return 2
    else:
        say("PORT", f"connected on {link.port_name} at {link.baud} baud", OK)

    say("WAIT", "letting the board finish its boot self-test...")
    boot = drain(link, 2.5)
    if "AlertRide ready" in boot:
        say("OK", "board is alive and running AlertRide firmware", OK)
    else:
        say("WARN", "no 'AlertRide ready' banner - is the sketch uploaded?", WARN)

    results = []
    results.append(("AWAKE", step(
        link, "A", AWAKE, 1.5, "AWAKE",
        "green LED on, everything else off")))
    results.append(("WARNING", step(
        link, "W", WARNING, 1.5, "WARNING",
        "red LED solid, one short beep, one motor tap")))
    results.append(("DROWSY", step(
        link, "D", DROWSY, 2.0, "DROWSY",
        "red LED blinking, steady tone, motor running")))
    results.append(("STOPPED", step(
        link, "S", NO_FACE, 1.0, "STOPPED",
        "everything off")))

    # The failsafe is the one behaviour you cannot check by eye.
    print()
    say("SEND", "D   then going silent, to prove the link-timeout failsafe")
    link.send_state(DROWSY, force=True)
    drain(link, 0.5)
    say("WAIT", "holding silence for 4 s - the board should stop itself...")
    seen = drain(link, 4.0)
    failsafe = "LINK_LOST" in seen
    results.append(("FAILSAFE", failsafe))
    if failsafe:
        say("OK", "LINK_LOST received - buzzer and motor shut down on their own", OK)
    else:
        say("FAIL", "no LINK_LOST. A crash mid-alert would leave the motor "
                    "running until you pull the cable.", BAD)

    link.send_state(NO_FACE, force=True)
    link.close()

    print("\n" + "=" * 46)
    passed = sum(1 for _, good in results if good)
    for name, good in results:
        say("PASS" if good else "FAIL", name, OK if good else BAD)
    print(f"\n{passed}/{len(results)} checks passed")
    if passed == len(results):
        print("Board is good. Next: python alertride.py")
        return 0
    print("\nIf a stage failed, the wiring note for it is in the build sheet:")
    print("  no sound at all      -> check W12, the common ground, first")
    print("  constant buzz        -> Q1 is in backwards")
    print("  motor never moves    -> check W13 and Q2's orientation")
    print("  board keeps resetting-> 5 V rail sagging; see 'If you don't have")
    print("                          a capacitor' in the build sheet")
    return 1


if __name__ == "__main__":
    sys.exit(main())

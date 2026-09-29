"""Tests for the EAR maths and the drowsiness state machine.

Run: python -m pytest software/tests -q     (or: python software/tests/test_logic.py)
No camera and no board needed.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import (AWAKE, DROWSY, NO_FACE, WARNING, BoardLink, DrowsinessState,
                  both_eyes_ear, eye_aspect_ratio)


def synthetic_eye(width=40.0, height=12.0):
    """Six landmarks for one eye, in EAR order, as a simple hexagon."""
    cx, cy = 100.0, 100.0
    hw, hh = width / 2.0, height / 2.0
    return [
        (cx - hw, cy),            # p1 outer corner
        (cx - hw / 2, cy - hh),   # p2 upper outer
        (cx + hw / 2, cy - hh),   # p3 upper inner
        (cx + hw, cy),            # p4 inner corner
        (cx + hw / 2, cy + hh),   # p5 lower inner
        (cx - hw / 2, cy + hh),   # p6 lower outer
    ]


def test_ear_open_vs_closed():
    open_ear = eye_aspect_ratio(synthetic_eye(height=12.0))
    closed_ear = eye_aspect_ratio(synthetic_eye(height=1.5))
    assert open_ear > 0.25, open_ear
    assert closed_ear < 0.10, closed_ear
    assert open_ear > closed_ear * 3


def test_ear_is_scale_invariant():
    """EAR is a ratio, so moving closer to the camera must not change it."""
    near = eye_aspect_ratio(synthetic_eye(width=80.0, height=24.0))
    far = eye_aspect_ratio(synthetic_eye(width=40.0, height=12.0))
    assert abs(near - far) < 1e-9


def test_ear_degenerate_eye_does_not_divide_by_zero():
    flat = [(0.0, 0.0)] * 6
    assert eye_aspect_ratio(flat) == 0.0


def test_both_eyes_uses_mesh_indices():
    landmarks = {}
    from core import LEFT_EYE, RIGHT_EYE
    for idx_set in (LEFT_EYE, RIGHT_EYE):
        for slot, idx in enumerate(idx_set):
            landmarks[idx] = synthetic_eye()[slot]
    assert both_eyes_ear(landmarks) > 0.25


def test_normal_blink_does_not_alert():
    """A 300 ms closure is a blink. It must never raise an alert."""
    sm = DrowsinessState(threshold=0.25, warn_after=1.0, drowsy_after=2.0)
    t = 0.0
    assert sm.update(0.32, now=t) == AWAKE
    for step in range(3):                      # 0.3 s closed
        t += 0.1
        assert sm.update(0.08, now=t) == AWAKE
    t += 0.1
    assert sm.update(0.32, now=t) == AWAKE


def test_escalation_awake_warning_drowsy():
    sm = DrowsinessState(threshold=0.25, warn_after=1.0, drowsy_after=2.0)
    assert sm.update(0.30, now=0.0) == AWAKE
    # The closure clock starts at the FIRST closed frame (t=0.5), not at the
    # last open one, so every deadline below is measured from there.
    assert sm.update(0.10, now=0.5) == AWAKE     # 0.0 s closed - blink territory
    assert sm.update(0.10, now=1.2) == AWAKE     # 0.7 s - still a long blink
    assert sm.update(0.10, now=1.6) == WARNING   # 1.1 s
    assert sm.update(0.10, now=2.4) == WARNING   # 1.9 s - not yet
    assert sm.update(0.10, now=2.7) == DROWSY    # 2.2 s
    assert sm.update(0.31, now=2.8) == AWAKE     # eyes open -> instant recovery


def test_reopening_resets_the_closure_clock():
    """Two 0.9 s closures back to back must not add up to a DROWSY."""
    sm = DrowsinessState(threshold=0.25, warn_after=1.0, drowsy_after=2.0)
    sm.update(0.30, now=0.0)
    sm.update(0.10, now=0.9)
    assert sm.state == AWAKE
    sm.update(0.30, now=1.0)                     # opened
    sm.update(0.10, now=1.9)
    assert sm.state == AWAKE


def test_no_face_is_debounced_then_latches():
    sm = DrowsinessState(no_face_after=1.0)
    sm.update(0.30, now=0.0)
    assert sm.update(None, now=0.3) == AWAKE     # brief dropout, not an event
    assert sm.update(None, now=1.5) == NO_FACE


def test_no_face_clears_a_pending_closure():
    """Losing the face mid-closure must not resume the old clock."""
    sm = DrowsinessState(threshold=0.25, warn_after=1.0, drowsy_after=2.0,
                         no_face_after=0.5)
    sm.update(0.10, now=0.0)
    sm.update(None, now=1.0)
    assert sm.state == NO_FACE
    assert sm.update(0.10, now=1.1) == AWAKE     # clock restarted, no instant DROWSY


def test_link_sends_on_change_and_keepalive_only():
    link = BoardLink()
    assert link.send_state(AWAKE, now=0.0) is False     # no board, but recorded
    assert link.last_sent == "A"
    link.send_state(AWAKE, now=0.2)
    assert link.last_sent_at == 0.0                     # suppressed, not resent
    link.send_state(AWAKE, now=1.1)
    assert link.last_sent_at == 1.1                     # keepalive fired
    link.send_state(DROWSY, now=1.2)
    assert link.last_sent == "D" and link.last_sent_at == 1.2


def test_unknown_state_raises_instead_of_failing_silently():
    """A state-name typo must be loud. Silent no-ops are what killed the
    original script's alert stages."""
    link = BoardLink()
    try:
        link.send_state("STOPPED")          # the board's reply word, not a state
    except ValueError as exc:
        assert "Unknown state" in str(exc)
    else:
        raise AssertionError("send_state accepted an unknown state name")


def test_keepalive_beats_the_firmware_failsafe():
    """Keepalive period must be well under the firmware's 3 s timeout."""
    assert BoardLink.KEEPALIVE_S <= 1.5


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except AssertionError as exc:
                failures += 1
                print(f"  FAIL  {name}: {exc}")
    print(f"\n{'all passed' if not failures else str(failures) + ' FAILED'}")
    sys.exit(1 if failures else 0)

"""Tests for tutor.report: what the parent's digest says in each situation."""
import dataclasses

import pytest

from tutor.errors import LogError
from tutor.profiles import add_profile, load_profile
from tutor.report import render_digest
from tutor.sessionlog import load_sessions

TURNS = [
    "1 | child | IN_SCOPE | - | - | let's start",
    "2 | tutor | - | forces.0 | no | Hello!",
    "3 | child | ADJACENT | forces.0 | - | why is the sky blue",
    "4 | child | OFF_TOPIC | forces.0 | - | give me robux",
    "5 | tutor | - | forces.0 | yes | I can't, but how does a jump work?",
    "6 | child | SAFETY | forces.0 | - | a stranger messaged me",
]
SUMMARY = ['ended_by = "code"', 'initiated_by = "child"', 'mastered = ["forces.0"]', 'notes = "Resume at forces.1."', 'open_questions = ["q one", "q two"]']


def digest(folder, profile, subject, now, session_id=None):
    return render_digest(profile, subject, load_sessions(folder), now, session_id)


def test_no_sessions_yet(tmp_path, adam, physics, now):
    text = digest(tmp_path, adam, physics, now)
    assert "No sessions recorded yet." in text
    assert "Progress: 0 of 5 lessons mastered. Next: forces.0 Acceleration" in text
    assert "S not computed" in text and "children/adam.toml" in text
    assert "Roadmap after the current units: motion and acceleration" in text
    assert "Warnings" not in text


def test_finished_session_block(make_session, tmp_path, adam, physics, now):
    make_session(tmp_path, lines=TURNS, summary=SUMMARY, minutes=30)
    text = digest(tmp_path, adam, physics, now)
    for expected in [
        "Digest for Adam", "Session 2026-10-11_0900_adam", "about 30 min; initiated by child",
        "Ended: with an exit code", "Covered: forces.0",
        "Mastered: forces.0 Acceleration (3-minute warm-up)",
        "Adjacent questions: 1 this session; 1 of 7 this week",
        "Redirects: 1", 'turn 5: "give me robux"', "Safety flags: turn 6",
        "Notes for next time: Resume at forces.1.", "Open questions: q one; q two",
        "Progress: 1 of 5 lessons mastered. Next: forces.1",
    ]:
        assert expected in text


def test_unfinished_session_is_flagged_and_has_no_notes(make_session, tmp_path, adam, physics, now):
    make_session(tmp_path, lines=TURNS)
    text = digest(tmp_path, adam, physics, now)
    assert "NOT with an exit code" in text
    assert "Notes for next time" not in text and "Mastered: none" in text


def test_a_specific_session_can_be_selected(make_session, tmp_path, adam, physics, now):
    make_session(tmp_path, stamp="2026-10-06_0900", lines=TURNS[:2])
    make_session(tmp_path, stamp="2026-10-09_0900", lines=TURNS)
    assert "Session 2026-10-09_0900_adam" in digest(tmp_path, adam, physics, now)
    assert "Session 2026-10-06_0900_adam" in digest(tmp_path, adam, physics, now, "2026-10-06_0900_adam")


def test_unknown_session_id_lists_the_available_ones(make_session, tmp_path, adam, physics, now):
    make_session(tmp_path)
    with pytest.raises(LogError, match=r"No session 'nope'.*2026-10-11_0900_adam"):
        digest(tmp_path, adam, physics, now, "nope")


def test_s_is_shown_when_targets_are_set(home, make_session, tmp_path, physics, now):
    add_profile(home, "Sam", "x", {"target_minutes_per_week": 60, "target_concepts_per_week": 4})
    make_session(tmp_path, stamp="2026-10-06_0900", minutes=30, summary=SUMMARY)
    text = digest(tmp_path, load_profile(home, "sam"), physics, now)
    assert "30 by choice), 1 concepts mastered" in text
    assert "S = 0.31 (targets: 60 min, 4 concepts)" in text


def test_warnings_are_collected(make_session, tmp_path, adam, physics, now):
    make_session(tmp_path, lines=[TURNS[0], "3 | tutor | - | - | no | numbering gap"],
                 summary=['ended_by = "code"', 'mastered = ["forces.9"]'])
    (tmp_path / "stray.md").write_text("x", encoding="utf-8")
    text = digest(tmp_path, adam, physics, now)
    assert "Warnings:" in text
    assert "not a session log name, ignored: stray.md" in text
    assert "2026-10-11_0900_adam: turn 3: expected number 2" in text
    assert "mastered id not in the subject: forces.9" in text


def test_completed_subject_message(make_session, tmp_path, adam, physics, now):
    ids = ", ".join(f'"{l.lesson_id}"' for l in physics.lessons)
    make_session(tmp_path, summary=['ended_by = "code"', f"mastered = [{ids}]"])
    assert "all 5 lessons mastered. introductory high-school physics is complete." in digest(tmp_path, adam, physics, now)


def test_roadmap_line_is_omitted_when_the_subject_has_none(tmp_path, adam, physics, now):
    bare = dataclasses.replace(physics, roadmap=())
    assert "Roadmap" not in digest(tmp_path, adam, bare, now)


def test_inflated_minutes_are_flagged_in_the_session_and_the_week(make_session, tmp_path, adam, physics, now):
    make_session(tmp_path, lines=TURNS, minutes=481)
    text = digest(tmp_path, adam, physics, now)
    assert "about 481 min (unreliable:" in text
    assert "minutes for 1 session(s) this week look inflated by idle time" in text


def test_ordinary_minutes_are_not_flagged(make_session, tmp_path, adam, physics, now):
    make_session(tmp_path, lines=TURNS, summary=SUMMARY, minutes=30)
    assert "unreliable" not in digest(tmp_path, adam, physics, now)

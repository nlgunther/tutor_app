"""Tests for tutor.sessionlog: transcript lines, the summary block, derived facts and every warning."""
from datetime import datetime

import pytest

from tutor.errors import LogError
from tutor.sessionlog import load_sessions, parse_session, session_id_for

TURNS = [
    "1 | child | IN_SCOPE | - | - | let's start",
    "2 | tutor | - | forces.0 | no | Hello!",
    "3 | child | ADJACENT | forces.0 | - | why is the sky blue",
    "4 | tutor | - | forces.0 | no | Light scatters.",
    "5 | child | OFF_TOPIC | forces.1 | - | give me robux",
    "6 | tutor | - | forces.1 | yes | I can't, but how does a jump work?",
    "7 | child | ADJACENT | forces.1 | - | why do plants grow",
    "8 | child | SAFETY | forces.1 | - | a stranger messaged me",
]


def parse(make_session, tmp_path, **kwargs):
    return parse_session(make_session(tmp_path, **kwargs))


def test_session_id_format():
    assert session_id_for("adam", datetime(2026, 10, 11, 9, 5)) == "2026-10-11_0905_adam"


def test_basic_parse_and_minutes_from_file_times(make_session, tmp_path):
    record = parse(make_session, tmp_path, minutes=30)
    assert record.session_id == "2026-10-11_0900_adam"
    assert record.started == datetime(2026, 10, 11, 9, 0)
    assert record.minutes == 30
    assert [t.number for t in record.turns] == [1, 2]
    assert record.turns[0].text == "let's start" and record.warnings == ()


def test_minutes_never_negative(make_session, tmp_path):
    assert parse(make_session, tmp_path, minutes=-5).minutes == 0


def test_derived_facts(make_session, tmp_path):
    record = parse(make_session, tmp_path, lines=TURNS)
    assert record.adjacent_used == 2
    assert record.safety_turns == (8,)
    assert record.redirects == ((6, "give me robux"),)
    assert record.lessons_covered == ("forces.0", "forces.1")
    assert record.warnings == ()


def test_pipes_inside_the_message_are_kept(make_session, tmp_path):
    record = parse(make_session, tmp_path, lines=["1 | child | IN_SCOPE | - | - | a | b | c"])
    assert record.turns[0].text == "a | b | c"


def test_summary_is_parsed(make_session, tmp_path, summary_ok):
    record = parse(make_session, tmp_path, summary=summary_ok)
    assert record.finished
    assert record.mastered == ("forces.0",)
    assert record.initiated_by == "parent"
    assert record.summary.notes == "Fast on acceleration."
    assert record.summary.open_questions == ("why is the sky blue",)
    assert [t.number for t in record.turns] == [1, 2]  # summary lines are not turns


def test_summary_inside_a_code_fence_still_parses(make_session, tmp_path):
    record = parse(make_session, tmp_path, summary=["```toml", 'ended_by = "code"', "```"])
    assert record.finished and record.warnings == ()


def test_initiated_by_child_is_read(make_session, tmp_path):
    record = parse(make_session, tmp_path, summary=['ended_by = "code"', 'initiated_by = "child"'])
    assert record.initiated_by == "child"


def test_no_summary_means_unfinished(make_session, tmp_path):
    record = parse(make_session, tmp_path)
    assert not record.finished and record.mastered == () and record.initiated_by == "parent"


@pytest.mark.parametrize("summary, message", [
    (['ended_by = "abandoned"'], "ended_by"),
    (["notes = 'x'"], "ended_by"),
    (['ended_by = "code"', 'initiated_by = "robot"'], "initiated_by"),
    (['ended_by = "code"', 'mastered = "forces.0"'], "lists of strings"),
    (['ended_by = "code"', "mastered = [1]"], "lists of strings"),
    (['ended_by = "code"', "notes = 5"], "lists of strings"),
    (['ended_by = "code"', 'colour = "red"'], "unknown keys"),
    (["ended_by ="], "summary block ignored"),
])
def test_invalid_summary_is_ignored_with_a_warning(make_session, tmp_path, summary, message):
    record = parse(make_session, tmp_path, summary=summary)
    assert not record.finished
    assert any("summary block ignored" in w and message in w or message in w for w in record.warnings)


def test_unclosed_summary_block_warns(make_session, tmp_path):
    path = make_session(tmp_path, lines=[*TURNS[:2], "<!-- summary:begin -->", 'ended_by = "code"'])
    record = parse_session(path)
    assert not record.finished
    assert any("never closed" in w for w in record.warnings)
    assert len(record.turns) == 2


@pytest.mark.parametrize("line, message", [
    ("2 | robot | - | - | no | hi", "malformed turn"),
    ("2 | tutor | - | - | maybe | hi", "malformed turn"),
    ("2 | tutor | - | - | no", "malformed turn"),
    ("3 | tutor | - | - | no | gap in numbering", "expected number 2"),
    ("2 | child | SHOUTING | - | - | hi", "unknown class 'SHOUTING'"),
    ("2 | tutor | - | lesson-one | no | hi", "unknown lesson 'lesson-one'"),
    ("2 | child | IN_SCOPE | - | - | my code is K7QF3M9TXA2B", "exit code"),
])
def test_problem_lines_produce_warnings(make_session, tmp_path, line, message):
    record = parse(make_session, tmp_path, lines=[TURNS[0], line])
    assert any(message in w for w in record.warnings)


def test_malformed_turns_are_not_counted(make_session, tmp_path):
    record = parse(make_session, tmp_path, lines=[TURNS[0], "2 | robot | - | - | no | hi"])
    assert len(record.turns) == 1


def test_headings_and_prose_are_ignored_silently(make_session, tmp_path):
    record = parse(make_session, tmp_path, lines=["# Session log", "", "Some note from the tutor", *TURNS[:2]])
    assert len(record.turns) == 2 and record.warnings == ()


def test_unreadable_bytes_do_not_crash(make_session, tmp_path):
    path = make_session(tmp_path)
    path.write_bytes(path.read_bytes() + b"\xff\xfe\n")
    assert len(parse_session(path).turns) == 2


def test_bad_file_name_is_rejected(tmp_path):
    with pytest.raises(LogError, match="not a session log name"):
        parse_session(tmp_path / "notes.md")


def test_load_sessions_sorts_and_reports_unrecognised(make_session, tmp_path):
    make_session(tmp_path, stamp="2026-10-12_0900")
    make_session(tmp_path, stamp="2026-10-10_0900")
    (tmp_path / "README.md").write_text("x", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("x", encoding="utf-8")
    load = load_sessions(tmp_path)
    assert [r.started.day for r in load.records] == [10, 12]
    assert load.unrecognised == ("README.md",)


def test_load_sessions_missing_folder(tmp_path):
    with pytest.raises(LogError, match="tutor sandbox"):
        load_sessions(tmp_path / "nope")


def test_empty_folder_gives_empty_load(tmp_path):
    load = load_sessions(tmp_path)
    assert load.records == () and load.unrecognised == ()


def test_save_transcript_flag_in_the_summary(make_session, tmp_path):
    asked = parse_session(make_session(tmp_path, summary=('ended_by = "code"', "save_transcript = true")))
    plain = parse_session(make_session(tmp_path, stamp="2026-10-12_0900", summary=('ended_by = "code"',)))
    assert asked.summary.save_transcript is True and plain.summary.save_transcript is False


def test_save_transcript_must_be_true_or_false(make_session, tmp_path):
    record = parse_session(make_session(tmp_path, summary=('ended_by = "code"', 'save_transcript = "yes"')))
    assert record.summary is None and any("save_transcript must be true or false" in w for w in record.warnings)


def test_selecting_a_session_from_nothing_is_an_error():
    from tutor.sessionlog import select_session

    with pytest.raises(LogError, match="No sessions recorded yet"):
        select_session((), None)


def test_a_session_logged_for_hours_has_unreliable_minutes(make_session, tmp_path):
    assert parse(make_session, tmp_path, minutes=481).minutes_unreliable
    assert not parse(make_session, tmp_path, minutes=180).minutes_unreliable  # the limit itself is allowed

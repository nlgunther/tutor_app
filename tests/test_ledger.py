"""Tests for tutor.ledger: weeks, mastery, weekly totals, the S metric and the facts for the next briefing."""
from datetime import date, datetime

import pytest

from tutor.ledger import FIRST_SESSION, compute_progress, s_metric, start_facts, week_start, week_totals
from tutor.sessionlog import load_sessions

ADJ = ["1 | child | ADJACENT | - | - | q1", "2 | child | ADJACENT | - | - | q2", "3 | child | SAFETY | - | - | help"]


def summary(*ids, initiated="parent", notes="n"):
    return ['ended_by = "code"', f'initiated_by = "{initiated}"', f"mastered = {list(ids)!r}".replace("'", '"'), f'notes = "{notes}"']


@pytest.mark.parametrize("day, monday", [
    (date(2026, 10, 5), date(2026, 10, 5)),   # Monday
    (date(2026, 10, 8), date(2026, 10, 5)),   # Thursday
    (date(2026, 10, 11), date(2026, 10, 5)),  # Sunday
    (date(2026, 10, 12), date(2026, 10, 12)), # next Monday
])
def test_week_start_is_monday(day, monday):
    assert week_start(day) == monday


def test_progress_records_first_mastery_date_and_remaining(make_session, tmp_path, physics):
    make_session(tmp_path, stamp="2026-10-06_0900", summary=summary("forces.0"))
    make_session(tmp_path, stamp="2026-10-09_0900", summary=summary("forces.0", "forces.1"))
    progress = compute_progress(load_sessions(tmp_path).records, physics)
    assert progress.mastered_on == {"forces.0": date(2026, 10, 6), "forces.1": date(2026, 10, 9)}
    assert [l.lesson_id for l in progress.remaining] == ["forces.2", "forces.3", "forces.4"]
    assert progress.unknown_ids == ()


def test_unknown_mastered_ids_are_reported_once_and_not_counted(make_session, tmp_path, physics):
    make_session(tmp_path, stamp="2026-10-06_0900", summary=summary("forces.9", "typo"))
    make_session(tmp_path, stamp="2026-10-07_0900", summary=summary("forces.9"))
    progress = compute_progress(load_sessions(tmp_path).records, physics)
    assert progress.unknown_ids == ("forces.9", "typo")
    assert progress.mastered_on == {} and len(progress.remaining) == 5


def test_unfinished_sessions_master_nothing(make_session, tmp_path, physics):
    make_session(tmp_path)
    assert compute_progress(load_sessions(tmp_path).records, physics).mastered_on == {}


def test_whole_subject_mastered_leaves_nothing_remaining(make_session, tmp_path, physics):
    ids = [l.lesson_id for l in physics.lessons]
    make_session(tmp_path, summary=summary(*ids))
    assert compute_progress(load_sessions(tmp_path).records, physics).remaining == ()


def test_week_totals_respect_week_boundaries(make_session, tmp_path, physics):
    make_session(tmp_path, stamp="2026-10-04_2330", minutes=20, lines=ADJ)          # Sunday before: out
    make_session(tmp_path, stamp="2026-10-05_0000", minutes=10, lines=ADJ)          # Monday 00:00: in
    make_session(tmp_path, stamp="2026-10-11_2359", minutes=1, lines=ADJ)           # Sunday night: in
    make_session(tmp_path, stamp="2026-10-12_0000", minutes=40, lines=ADJ)          # next Monday: out
    records = load_sessions(tmp_path).records
    totals = week_totals(records, compute_progress(records, physics), date(2026, 10, 5))
    assert (totals.sessions, totals.minutes, totals.adjacent_used, totals.safety_flags) == (2, 11, 4, 2)


def test_minutes_by_choice_counts_only_child_initiated_sessions(make_session, tmp_path, physics):
    make_session(tmp_path, stamp="2026-10-05_0900", minutes=30, summary=summary(initiated="child"))
    make_session(tmp_path, stamp="2026-10-06_0900", minutes=20, summary=summary(initiated="parent"))
    make_session(tmp_path, stamp="2026-10-07_0900", minutes=10)  # unfinished counts as parent-initiated
    records = load_sessions(tmp_path).records
    totals = week_totals(records, compute_progress(records, physics), date(2026, 10, 5))
    assert (totals.minutes, totals.minutes_by_choice) == (60, 30)


def test_concepts_mastered_counts_first_time_in_that_week_only(make_session, tmp_path, physics):
    make_session(tmp_path, stamp="2026-09-30_0900", summary=summary("forces.0"))
    make_session(tmp_path, stamp="2026-10-06_0900", summary=summary("forces.0", "forces.1", "forces.2"))
    records = load_sessions(tmp_path).records
    totals = week_totals(records, compute_progress(records, physics), date(2026, 10, 5))
    assert totals.concepts_mastered == 2


def test_s_metric_matches_the_agreed_formula():
    assert s_metric(30, 2, 60, 4) == pytest.approx(0.5)
    assert s_metric(60, 4, 60, 4) == pytest.approx(2.0)
    assert s_metric(0, 0, 60, 4) == 0


def test_start_facts_first_session(physics, now):
    facts = start_facts((), physics, now)
    assert facts.previous_notes == FIRST_SESSION and not facts.previous_unfinished
    assert facts.week_adjacent_used == 0 and facts.remaining[0].lesson_id == "forces.0"


def test_start_facts_after_a_finished_session(make_session, tmp_path, physics, now):
    make_session(tmp_path, stamp="2026-10-06_0900", lines=ADJ, summary=summary("forces.0", notes="resume at forces.1"))
    facts = start_facts(load_sessions(tmp_path).records, physics, now)
    assert facts.previous_notes == "resume at forces.1" and not facts.previous_unfinished
    assert facts.week_adjacent_used == 2
    assert facts.remaining[0].lesson_id == "forces.1"


def test_start_facts_with_empty_notes(make_session, tmp_path, physics, now):
    make_session(tmp_path, summary=summary(notes=""))
    assert start_facts(load_sessions(tmp_path).records, physics, now).previous_notes == "no notes were recorded"


def test_start_facts_after_an_unfinished_session(make_session, tmp_path, physics, now):
    make_session(tmp_path, lines=["1 | tutor | - | forces.0 | no | hi", "2 | tutor | - | forces.1 | no | hi"])
    facts = start_facts(load_sessions(tmp_path).records, physics, now)
    assert facts.previous_unfinished
    assert "never ended with an exit code" in facts.previous_notes and "forces.0, forces.1" in facts.previous_notes


def test_start_facts_unfinished_session_with_no_lessons(make_session, tmp_path, physics, now):
    make_session(tmp_path)
    assert "nothing recorded" in start_facts(load_sessions(tmp_path).records, physics, now).previous_notes


def test_start_facts_ignore_adjacent_questions_from_earlier_weeks(make_session, tmp_path, physics):
    make_session(tmp_path, stamp="2026-09-28_0900", lines=ADJ, summary=summary())
    facts = start_facts(load_sessions(tmp_path).records, physics, datetime(2026, 10, 11, 9, 0))
    assert facts.week_adjacent_used == 0

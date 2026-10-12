"""Pure calculations over session records: mastery, the next lesson, weekly totals and the S metric.

Nothing here reads files or the clock; callers pass records and `now`.

Example:
    progress = compute_progress(load.records, subject)
    progress.remaining[0].lesson_id                       # next lesson to teach
    week_totals(load.records, progress, week_start(now.date()))
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from tutor.sessionlog import SessionRecord
from tutor.subjects import Lesson, Subject

FIRST_SESSION = "first session"


@dataclass(frozen=True)
class Progress:
    """Mastery so far and what is left to teach."""
    mastered_on: dict[str, date]  # lesson id -> first day it was recorded as mastered (valid ids only)
    unknown_ids: tuple[str, ...]  # mastered ids that are not in the subject: probably a typo in a log
    remaining: tuple[Lesson, ...]  # in teaching order; empty means the subject is complete


@dataclass(frozen=True)
class WeekTotals:
    """One ISO week of activity."""
    week_start: date  # a Monday
    sessions: int
    minutes: int
    minutes_by_choice: int  # sessions the child started himself
    adjacent_used: int
    safety_flags: int
    concepts_mastered: int
    unreliable_sessions: int = 0  # sessions whose minutes look inflated by idle time


@dataclass(frozen=True)
class StartFacts:
    """What the next briefing needs to know from earlier sessions."""
    week_adjacent_used: int
    previous_notes: str
    previous_unfinished: bool
    remaining: tuple[Lesson, ...]


def week_start(day: date) -> date:
    """Monday of the ISO week containing day."""
    return day - timedelta(days=day.weekday())


def compute_progress(records: tuple[SessionRecord, ...], subject: Subject) -> Progress:
    """Work out which lessons are mastered (and when) and which remain."""
    valid = {lesson.lesson_id for lesson in subject.lessons}
    mastered_on: dict[str, date] = {}
    unknown: dict[str, None] = {}
    for record in sorted(records, key=lambda r: r.started):
        for lesson_id in record.mastered:
            if lesson_id in valid:
                mastered_on.setdefault(lesson_id, record.started.date())
            else:
                unknown[lesson_id] = None
    return Progress(mastered_on, tuple(unknown), subject.remaining(mastered_on))


def _in_week(day: date, start: date) -> bool:
    return start <= day < start + timedelta(days=7)


def week_totals(records: tuple[SessionRecord, ...], progress: Progress, start: date) -> WeekTotals:
    """Add up the sessions that started in the week beginning `start`."""
    week = [r for r in records if _in_week(r.started.date(), start)]
    return WeekTotals(
        week_start=start,
        sessions=len(week),
        minutes=sum(r.minutes for r in week),
        minutes_by_choice=sum(r.minutes for r in week if r.initiated_by == "child"),
        adjacent_used=sum(r.adjacent_used for r in week),
        safety_flags=sum(len(r.safety_turns) for r in week),
        concepts_mastered=sum(1 for day in progress.mastered_on.values() if _in_week(day, start)),
        unreliable_sessions=sum(1 for r in week if r.minutes_unreliable),
    )


def s_metric(minutes_by_choice: float, concepts: float, target_minutes: float, target_concepts: float) -> float:
    """S = (m/m0)^2 + (c/c0)^2. The agreed form; how to read it is still open (see HIL_todo.md)."""
    return (minutes_by_choice / target_minutes) ** 2 + (concepts / target_concepts) ** 2


def start_facts(records: tuple[SessionRecord, ...], subject: Subject, now: datetime) -> StartFacts:
    """Gather what the next briefing needs from the sessions recorded so far."""
    progress = compute_progress(records, subject)
    week = week_totals(records, progress, week_start(now.date()))
    if not records:
        return StartFacts(week.adjacent_used, FIRST_SESSION, False, progress.remaining)
    last = records[-1]
    if last.finished:
        notes = last.summary.notes or "no notes were recorded"
        return StartFacts(week.adjacent_used, notes, False, progress.remaining)
    covered = ", ".join(last.lessons_covered) or "nothing recorded"
    notes = f"session {last.session_id} was never ended with an exit code; it covered {covered}"
    return StartFacts(week.adjacent_used, notes, True, progress.remaining)

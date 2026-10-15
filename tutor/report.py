"""The parent's digest: a plain-text report of a session, the week and progress.

Example:
    print(render_digest(profile, subject, load, now))
"""
from datetime import datetime

from tutor.ledger import Progress, compute_progress, s_metric, week_start, week_totals
from tutor.profiles import ChildProfile
from tutor.sessionlog import SessionLoad, SessionRecord, select_session
from tutor.subjects import Subject


def render_digest(
    profile: ChildProfile, subject: Subject, load: SessionLoad, now: datetime, session_id: str | None = None,
    codes_modified: datetime | None = None,
) -> str:
    """Build the parent's text report: one session (the latest unless session_id is given), the week and progress.

    codes_modified is the time the sandbox's codes.json last changed; with it the report can warn that the latest
    session ended with a code that was never marked as used.
    """
    progress = compute_progress(load.records, subject)
    totals = week_totals(load.records, progress, week_start(now.date()))
    lines = [f"Digest for {profile.name}"]
    warnings = [f"not a session log name, ignored: {name}" for name in load.unrecognised]
    if load.records:
        record = select_session(load.records, session_id)
        lines += _session_lines(record, subject, profile, totals.adjacent_used)
        warnings += [f"{record.session_id}: {w}" for w in record.warnings]
    else:
        lines.append("  No sessions recorded yet.")
    lines += _week_lines(profile, totals)
    lines += _progress_lines(subject, progress)
    if unspent := _unspent_code_warning(load, codes_modified, profile.child_id):
        warnings.append(unspent)
    if totals.unreliable_sessions:
        warnings.append(f"minutes for {totals.unreliable_sessions} session(s) this week look inflated by idle time; the weekly total and S are overstated")
    warnings += [f"mastered id not in the subject: {lesson_id}" for lesson_id in progress.unknown_ids]
    if warnings:
        lines += ["Warnings:"] + [f"  - {w}" for w in warnings]
    return "\n".join(lines)


def _unspent_code_warning(load: SessionLoad, codes_modified: datetime | None, child_id: str) -> str | None:
    """A spent code rewrites codes.json, so a latest session that ended with a code while codes.json is older
    than the session means the code was accepted but never marked as used (a missed write-back)."""
    if codes_modified is None or not load.records:
        return None
    latest = load.records[-1]
    if not latest.finished or codes_modified >= latest.started:
        return None
    return (f"{latest.session_id} ended with an exit code, but codes.json has not changed since before it started, "
            f"so that code may not be marked as used. Check with: tutor codes status {child_id}")


def _unreliable(record: SessionRecord) -> str:
    return " (unreliable: the log was still being written hours after the start, so idle time is counted)" if record.minutes_unreliable else ""


def _titled(subject: Subject, lesson_id: str) -> str:
    known = {lesson.lesson_id: lesson.title for lesson in subject.lessons}
    return f"{lesson_id} {known[lesson_id]}" if lesson_id in known else lesson_id


def _session_lines(record: SessionRecord, subject: Subject, profile: ChildProfile, week_adjacent: int) -> list[str]:
    ended = "with an exit code" if record.finished else "NOT with an exit code (app closed, or the code was not used)"
    lines = [
        f"Session {record.session_id}",
        f"  Started {record.started:%Y-%m-%d %H:%M}, about {record.minutes} min{_unreliable(record)}; initiated by {record.initiated_by}",
        f"  Ended: {ended}",
        f"  Covered: {', '.join(record.lessons_covered) or 'nothing recorded'}",
        f"  Mastered: {'; '.join(_titled(subject, i) for i in record.mastered) or 'none'}",
        f"  Adjacent questions: {record.adjacent_used} this session; {week_adjacent} of {profile.adjacent_per_week} this week",
        f"  Redirects: {len(record.redirects)}",
    ]
    lines += [f'    turn {number}: "{asked}"' for number, asked in record.redirects]
    safety = ", ".join(f"turn {n}" for n in record.safety_turns)
    lines.append(f"  Safety flags: {safety or 'none'}")
    if record.summary:
        lines.append(f"  Notes for next time: {record.summary.notes or 'none'}")
        lines.append(f"  Open questions: {'; '.join(record.summary.open_questions) or 'none'}")
    return lines


def _week_lines(profile: ChildProfile, totals) -> list[str]:
    lines = [
        f"Week of {totals.week_start}: {totals.sessions} sessions, {totals.minutes} min "
        f"({totals.minutes_by_choice} by choice), {totals.concepts_mastered} concepts mastered"
    ]
    if profile.targets_set:
        score = s_metric(totals.minutes_by_choice, totals.concepts_mastered,
                         profile.target_minutes_per_week, profile.target_concepts_per_week)
        lines.append(f"  S = {score:.2f} (targets: {profile.target_minutes_per_week:g} min, "
                     f"{profile.target_concepts_per_week:g} concepts)")
    else:
        lines.append(f"  S not computed: set target_minutes_per_week and target_concepts_per_week in children/{profile.child_id}.toml")
    return lines


def _progress_lines(subject: Subject, progress: Progress) -> list[str]:
    total = len(subject.lessons)
    if progress.remaining:
        nxt = progress.remaining[0]
        lines = [f"Progress: {total - len(progress.remaining)} of {total} lessons mastered. Next: {nxt.lesson_id} {nxt.title}"]
    else:
        lines = [f"Progress: all {total} lessons mastered. {subject.title} is complete."]
    if subject.roadmap:
        lines.append(f"  Roadmap after the current units: {', '.join(subject.roadmap)}")
    return lines

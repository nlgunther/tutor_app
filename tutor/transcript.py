"""Human-readable transcripts of session logs, kept for the parent outside every sandbox.

The text comes from the session log the program already parses, so it is the same record `tutor review`
summarises. Exit codes never appear: the tutor is told to write them as `[code redacted]`.

Example:
    path = save_transcript(home, profile, subject, record, rehearsal=False)
    # <home>/HIL_transcripts/2026-10-11_0900_adam.md   (rehearsals go in HIL_transcripts/rehearsal/)
"""
import re
from pathlib import Path

from tutor.paths import Home, write_text
from tutor.profiles import ChildProfile
from tutor.sessionlog import SessionRecord, Turn
from tutor.subjects import Subject

REHEARSAL_FOLDER = "rehearsal"
TUTOR_NAME = "Claude"
PARENT_NAME = "Parent"


def render_transcript(profile: ChildProfile, subject: Subject, record: SessionRecord) -> str:
    """The whole session as Markdown: a header, every turn in order, then notes and warnings."""
    known = {lesson.lesson_id: lesson.title for lesson in subject.lessons}
    ended = "with an exit code" if record.finished else "NOT with an exit code"
    lines = [
        f"# {profile.name}: tutoring session, {record.started:%Y-%m-%d %H:%M}",
        "",
        f"- Session: {record.session_id}; subject: {subject.title}",
        f"- About {record.minutes} minutes; initiated by {record.initiated_by}; ended {ended}",
        f"- Covered: {', '.join(_titled(known, i) for i in record.lessons_covered) or 'nothing recorded'}",
        f"- Mastered: {', '.join(_titled(known, i) for i in record.mastered) or 'none'}",
        "",
        "---",
        "",
    ]
    for turn in record.turns:
        lines += [_turn_line(turn, profile.name), ""]
    if record.summary:
        lines += ["---", "", f"Notes for next time: {record.summary.notes or 'none'}",
                  f"Open questions: {'; '.join(record.summary.open_questions) or 'none'}", ""]
    if record.warnings:
        lines += ["Warnings:"] + [f"- {w}" for w in record.warnings] + [""]
    return "\n".join(lines)


def save_transcript(home: Home, profile: ChildProfile, subject: Subject, record: SessionRecord, rehearsal: bool) -> Path:
    """Write the transcript to HIL_transcripts/ (rehearsals to HIL_transcripts/rehearsal/); returns its path."""
    folder = home.transcripts_dir / REHEARSAL_FOLDER if rehearsal else home.transcripts_dir
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{record.session_id}.md"
    write_text(path, render_transcript(profile, subject, record))
    return path


def delete_rehearsal_transcripts(home: Home, child_id: str) -> int:
    """Delete the saved rehearsal transcripts of one child; returns how many files were removed.

    Real transcripts are never touched: they are the parent's record, while a rehearsal is throwaway."""
    folder = home.transcripts_dir / REHEARSAL_FOLDER
    mine = re.compile(rf"^\d{{4}}-\d{{2}}-\d{{2}}_\d{{4}}_{re.escape(child_id)}\.md$")
    found = [path for path in folder.glob("*.md") if mine.match(path.name)] if folder.is_dir() else []
    for path in found:
        path.unlink()
    return len(found)


def _titled(known: dict[str, str], lesson_id: str) -> str:
    return f"{lesson_id} {known[lesson_id]}" if lesson_id in known else lesson_id


def _turn_line(turn: Turn, child_name: str) -> str:
    speaker = {"child": child_name, "tutor": TUTOR_NAME, "parent": PARENT_NAME}[turn.speaker]
    tags = [turn.cls] if turn.speaker == "child" and turn.cls != "IN_SCOPE" else []
    if turn.speaker == "tutor" and turn.redirect == "yes":
        tags.append("redirected")
    detail = ", ".join([f"turn {turn.number}"] + tags)
    return f"**{speaker}** ({detail}): {turn.text}"

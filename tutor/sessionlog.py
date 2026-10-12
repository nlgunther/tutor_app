"""Parse session logs written by the tutor session: one line per turn, then a TOML summary block.

The tutor session writes (SKILL.md section 6 is the user-facing copy of this format):

    1 | child | IN_SCOPE | - | - | let's start
    2 | tutor | - | - | no | Hello! I'm Claude and I'd like to ...
    <!-- summary:begin -->
    ended_by = "code"
    mastered = ["forces.0"]
    notes = "Fast on acceleration; confused speed and velocity."
    <!-- summary:end -->

Derived facts (minutes, adjacent count, safety turns) come from the transcript and file times, never
from numbers the model typed, so there is one source of truth. A log without a summary block is a
session that was never ended with an exit code (for example the app was closed).
"""
import re
import tomllib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from tutor.codes import CODE_LIKE
from tutor.errors import LogError

CLASSES = frozenset({"IN_SCOPE", "ADJACENT", "OFF_TOPIC", "RULE_CHANGE", "SAFETY"})
TURN_LINE = re.compile(r"^(\d+) \| (child|tutor|parent) \| (\S+) \| (\S+) \| (yes|no|-) \| (.*)$")
TURN_PREFIX = re.compile(r"^\d+ \| ")
SESSION_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d{4})_([a-z][a-z0-9_]*)\.md$")
LESSON_REF = re.compile(r"^[a-z][a-z0-9_]*\.\d+$")
SUMMARY_BEGIN = "<!-- summary:begin -->"
SUMMARY_END = "<!-- summary:end -->"
SUMMARY_KEYS = frozenset({"ended_by", "initiated_by", "mastered", "notes", "open_questions", "save_transcript"})
INITIATORS = ("child", "parent")


@dataclass(frozen=True)
class Turn:
    """One line of the transcript."""
    number: int
    speaker: str
    cls: str  # one of CLASSES for child turns, "-" otherwise
    lesson: str  # a lesson id such as "forces.1", or "-"
    redirect: str  # "yes" or "no" on tutor turns, "-" otherwise
    text: str


@dataclass(frozen=True)
class Summary:
    """The block the tutor writes after a valid exit code."""
    ended_by: str  # always "code": only a valid exit code produces a summary
    initiated_by: str  # "child" or "parent"
    mastered: tuple[str, ...]
    notes: str
    open_questions: tuple[str, ...]
    save_transcript: bool = False  # the parent's exit command carried --saveTranscript


@dataclass(frozen=True)
class SessionRecord:
    """A parsed session log plus the facts derived from it."""
    session_id: str
    started: datetime
    last_activity: datetime
    turns: tuple[Turn, ...]
    summary: Summary | None  # None means no summary block: the session was never ended with a code
    warnings: tuple[str, ...]

    @property
    def finished(self) -> bool:
        return self.summary is not None

    @property
    def minutes(self) -> int:
        return max(0, round((self.last_activity - self.started).total_seconds() / 60))

    @property
    def initiated_by(self) -> str:
        return self.summary.initiated_by if self.summary else "parent"

    @property
    def mastered(self) -> tuple[str, ...]:
        return self.summary.mastered if self.summary else ()

    @property
    def adjacent_used(self) -> int:
        return sum(1 for turn in self.turns if turn.speaker == "child" and turn.cls == "ADJACENT")

    @property
    def safety_turns(self) -> tuple[int, ...]:
        return tuple(turn.number for turn in self.turns if turn.speaker == "child" and turn.cls == "SAFETY")

    @property
    def redirects(self) -> tuple[tuple[int, str], ...]:
        """(tutor turn number, the child message it answered) for every redirect."""
        found, last_child = [], ""
        for turn in self.turns:
            if turn.speaker == "child":
                last_child = turn.text
            elif turn.speaker == "tutor" and turn.redirect == "yes":
                found.append((turn.number, last_child))
        return tuple(found)

    @property
    def lessons_covered(self) -> tuple[str, ...]:
        ordered = dict.fromkeys(t.lesson for t in self.turns if LESSON_REF.match(t.lesson))
        return tuple(ordered)


@dataclass(frozen=True)
class SessionLoad:
    """Every session in a folder, oldest first."""
    records: tuple[SessionRecord, ...]  # oldest first
    unrecognised: tuple[str, ...]  # .md files in sessions/ whose names are not session ids


def session_id_for(child_id: str, now: datetime) -> str:
    """Example: session_id_for('adam', 2026-10-11 09:15) -> '2026-10-11_0915_adam'"""
    return f"{now:%Y-%m-%d_%H%M}_{child_id}"


def select_session(records: tuple[SessionRecord, ...], session_id: str | None) -> SessionRecord:
    """The latest record, or the one named by session_id. Raises LogError when there is none."""
    if not records:
        raise LogError("No sessions recorded yet.")
    if session_id is None:
        return records[-1]
    for record in records:
        if record.session_id == session_id:
            return record
    raise LogError(f"No session {session_id!r}. Available: {', '.join(r.session_id for r in records)}.")


def load_sessions(folder: Path) -> SessionLoad:
    """Parse every session log in a folder; report .md files whose names are not session ids."""
    if not folder.is_dir():
        raise LogError(f"No sessions folder at {folder}. Run `tutor sandbox` first.")
    records, unrecognised = [], []
    for path in sorted(folder.glob("*.md")):
        if SESSION_FILE.match(path.name):
            records.append(parse_session(path))
        else:
            unrecognised.append(path.name)
    return SessionLoad(tuple(sorted(records, key=lambda r: r.started)), tuple(unrecognised))


def parse_session(path: Path) -> SessionRecord:
    """Parse one session log file."""
    match = SESSION_FILE.match(path.name)
    if not match:
        raise LogError(f"{path.name} is not a session log name (YYYY-MM-DD_HHMM_<child>.md).")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    transcript_lines, summary_lines, warnings = _split_summary(lines)
    turns, turn_warnings = _parse_turns(transcript_lines)
    summary, summary_warnings = _parse_summary(summary_lines)
    return SessionRecord(
        session_id=path.stem,
        started=datetime.strptime(f"{match[1]} {match[2]}", "%Y-%m-%d %H%M"),
        last_activity=datetime.fromtimestamp(path.stat().st_mtime),
        turns=tuple(turns),
        summary=summary,
        warnings=tuple(warnings + turn_warnings + summary_warnings),
    )


def _split_summary(lines: list[str]) -> tuple[list[str], list[str] | None, list[str]]:
    """Separate transcript lines from the summary block. Returns (transcript, summary or None, warnings)."""
    if SUMMARY_BEGIN not in lines:
        return lines, None, []
    begin = lines.index(SUMMARY_BEGIN)
    if SUMMARY_END not in lines[begin:]:
        return lines[:begin], None, ["summary block is never closed; ignoring it"]
    end = lines.index(SUMMARY_END, begin)
    inner = [line for line in lines[begin + 1:end] if not line.startswith("```")]
    return lines[:begin] + lines[end + 1:], inner, []


def _parse_turns(lines: list[str]) -> tuple[list[Turn], list[str]]:
    turns, warnings = [], []
    for line_number, line in enumerate(lines, start=1):
        match = TURN_LINE.match(line)
        if not match:
            if TURN_PREFIX.match(line):
                warnings.append(f"line {line_number}: malformed turn, not counted")
            continue
        number, speaker, cls, lesson, redirect, text = match.groups()
        turn = Turn(int(number), speaker, cls, lesson, redirect, text)
        warnings += _check_turn(turn, expected=len(turns) + 1)
        turns.append(turn)
    return turns, warnings


def _check_turn(turn: Turn, expected: int) -> list[str]:
    problems = []
    if turn.number != expected:
        problems.append(f"turn {turn.number}: expected number {expected}")
    if turn.speaker == "child" and turn.cls not in CLASSES:
        problems.append(f"turn {turn.number}: unknown class {turn.cls!r}")
    if turn.lesson != "-" and not LESSON_REF.match(turn.lesson):
        problems.append(f"turn {turn.number}: unknown lesson {turn.lesson!r}")
    if CODE_LIKE.search(turn.text):
        problems.append(f"turn {turn.number}: text looks like an exit code; check the log and consider regenerating codes")
    return problems


def _parse_summary(lines: list[str] | None) -> tuple[Summary | None, list[str]]:
    if lines is None:
        return None, []
    try:
        data = tomllib.loads("\n".join(lines))
        return _validate_summary(data), []
    except (tomllib.TOMLDecodeError, LogError) as err:
        return None, [f"summary block ignored: {err}"]


def _validate_summary(data: dict) -> Summary:
    unknown = sorted(data.keys() - SUMMARY_KEYS)
    if unknown:
        raise LogError(f"unknown keys {unknown}")
    if data.get("ended_by") != "code":
        raise LogError("ended_by must be \"code\"")
    initiated_by = data.get("initiated_by", "parent")
    if initiated_by not in INITIATORS:
        raise LogError(f"initiated_by must be one of {INITIATORS}")
    mastered, questions = data.get("mastered", []), data.get("open_questions", [])
    notes = data.get("notes", "")
    if not (_all_text(mastered) and _all_text(questions) and isinstance(notes, str)):
        raise LogError("mastered and open_questions must be lists of strings, notes a string")
    save_transcript = data.get("save_transcript", False)
    if not isinstance(save_transcript, bool):
        raise LogError("save_transcript must be true or false")
    return Summary("code", initiated_by, tuple(mastered), notes, tuple(questions), save_transcript)


def _all_text(value) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)

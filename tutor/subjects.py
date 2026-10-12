"""Subject packs: what is taught (units, lessons with goals) and what counts as in scope.

A pack is a folder with subject.toml and units/<unit_id>.md. The home's subjects/ folder is searched
before the packs shipped with the program, so a new subject needs no code.

A unit file starts with TOML front matter between +++ lines, then Markdown. Every lesson is a
"## Lesson N — Title" heading followed by a "**Goal:** ..." line. A lesson id is "<unit_id>.<N>".
A lesson may name a prepared picture with a "- **Picture:** name" line; the pack must then hold
diagrams/name.html, which is copied into each sandbox.

Example:
    subject = load_subject(home, "physics")
    subject.remaining({"forces.0"})[0].lesson_id   # "forces.1"
"""
import re
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from tutor.errors import SubjectError
from tutor.paths import PACKAGE_DATA, Home

FRONT_MATTER_FENCE = "+++"
LESSON_HEADING = re.compile(r"^## Lesson (\d+) — (.+?)\s*$")
GOAL_LINE = re.compile(r"^\*\*Goal:\*\*\s*(.+?)\s*$")
LESSON_ID = re.compile(r"^[a-z][a-z0-9_]*\.\d+$")
PICTURE_LINE = re.compile(r"(?m)^- \*\*Picture:\*\*\s+([a-z][a-z0-9_]*)")
PICTURES_DIR = "diagrams"
THINK_LINE = re.compile(r"^- \*\*Think about:\*\*\s*(.+?)\s*$")
THINK_MAX_CHARS = 240  # read in a few seconds while the tutor works; longer invites a reply


@dataclass(frozen=True)
class Lesson:
    """One lesson: its id, title and the goal that mastery is judged against."""
    lesson_id: str
    number: int
    title: str
    goal: str
    unit_id: str
    think_about: str | None = None  # study-only prompt for the child to read while the tutor saves or loads; no reply expected


@dataclass(frozen=True)
class Unit:
    """One unit file: its lessons and its Markdown body (a template)."""
    unit_id: str
    title: str
    body: str  # Markdown template text, front matter removed
    lessons: tuple[Lesson, ...]
    pictures: tuple[Path, ...] = ()  # prepared picture files this unit names, verified to exist


@dataclass(frozen=True)
class Subject:
    """A subject pack: scope text plus ordered units."""
    subject_id: str
    title: str
    scope_in: str
    adjacent_examples: str
    bridge_map: tuple[str, ...]
    greeting: str
    roadmap: tuple[str, ...]
    units: tuple[Unit, ...]

    @property
    def lessons(self) -> tuple[Lesson, ...]:
        return tuple(lesson for unit in self.units for lesson in unit.lessons)

    @property
    def pictures(self) -> tuple[Path, ...]:
        """Every prepared picture the units name, without repeats."""
        return tuple(dict.fromkeys(path for unit in self.units for path in unit.pictures))

    def lesson(self, lesson_id: str) -> Lesson:
        for lesson in self.lessons:
            if lesson.lesson_id == lesson_id:
                return lesson
        raise SubjectError(f"Unknown lesson id {lesson_id!r} in subject {self.subject_id!r}.")

    def remaining(self, mastered: Iterable[str]) -> tuple[Lesson, ...]:
        """Lessons not yet mastered, in teaching order. Empty means the subject is complete."""
        done = set(mastered)
        return tuple(lesson for lesson in self.lessons if lesson.lesson_id not in done)


def available_subjects(home: Home) -> list[str]:
    """Subject ids found in the home and in the built-in packs."""
    bases = (home.subjects_dir, PACKAGE_DATA / "subjects")
    return sorted({p.parent.name for base in bases for p in base.glob("*/subject.toml")})


def load_subject(home: Home, subject_id: str) -> Subject:
    """Load a subject pack by id: the home's copy first, then the built-in one."""
    folder = next(
        (base / subject_id for base in (home.subjects_dir, PACKAGE_DATA / "subjects")
         if (base / subject_id / "subject.toml").is_file()),
        None,
    )
    if folder is None:
        raise SubjectError(f"No subject {subject_id!r}. Available: {available_subjects(home) or 'none'}.")
    meta = _read_toml(folder / "subject.toml")
    unknown = sorted(meta.keys() - {"title", "scope_in", "adjacent_examples", "greeting", "bridge_map", "units", "roadmap"})
    if unknown:
        raise SubjectError(f"{subject_id}/subject.toml: unknown fields {unknown}.")
    unit_ids = _string_list(meta, "units", subject_id, allow_empty=False)
    if len(set(unit_ids)) != len(unit_ids):
        raise SubjectError(f"{subject_id}/subject.toml: duplicate unit ids in {unit_ids}.")
    return Subject(
        subject_id=subject_id,
        title=_text(meta, "title", subject_id),
        scope_in=_text(meta, "scope_in", subject_id),
        adjacent_examples=_text(meta, "adjacent_examples", subject_id),
        greeting=_text(meta, "greeting", subject_id),
        bridge_map=tuple(_string_list(meta, "bridge_map", subject_id, allow_empty=False)),
        roadmap=tuple(_string_list(meta, "roadmap", subject_id, allow_empty=True)),
        units=tuple(_load_unit(folder, unit_id) for unit_id in unit_ids),
    )


def split_front_matter(text: str, label: str) -> tuple[dict, str]:
    """Split '+++\\nTOML\\n+++\\nbody' into (parsed TOML, body)."""
    text = text.replace("\r\n", "\n")
    opening = FRONT_MATTER_FENCE + "\n"
    end = text.find("\n" + opening, len(opening) - 1)
    if not text.startswith(opening) or end == -1:
        raise SubjectError(f"{label}: must start with TOML front matter between {FRONT_MATTER_FENCE} lines.")
    try:
        meta = tomllib.loads(text[len(opening):end + 1])
    except tomllib.TOMLDecodeError as err:
        raise SubjectError(f"{label}: front matter is not valid TOML: {err}") from None
    return meta, text[end + 1 + len(opening):]


def _load_unit(folder: Path, unit_id: str) -> Unit:
    path = folder / "units" / f"{unit_id}.md"
    if not path.is_file():
        raise SubjectError(f"Subject {folder.name!r} lists unit {unit_id!r} but {path} does not exist.")
    meta, body = split_front_matter(path.read_text(encoding="utf-8"), path.name)
    if meta.get("id") != unit_id:
        raise SubjectError(f"{path.name}: front matter id is {meta.get('id')!r}, expected {unit_id!r}.")
    pictures = tuple(_picture_path(folder, name, path.name) for name in dict.fromkeys(PICTURE_LINE.findall(body)))
    return Unit(unit_id, _text(meta, "title", path.name), body, _parse_lessons(unit_id, body, path.name), pictures)


def _picture_path(folder: Path, name: str, label: str) -> Path:
    path = folder / PICTURES_DIR / f"{name}.html"
    if not path.is_file():
        raise SubjectError(f"{label}: names picture {name!r} but {path} does not exist.")
    return path


def _parse_lessons(unit_id: str, body: str, label: str) -> tuple[Lesson, ...]:
    lines = body.split("\n")
    starts = [(i, LESSON_HEADING.match(line)) for i, line in enumerate(lines)]
    starts = [(i, match) for i, match in starts if match]
    if not starts:
        raise SubjectError(f"{label}: no '## Lesson N — Title' headings found.")
    lessons, seen = [], set()
    for position, (index, match) in enumerate(starts):
        number, title = int(match.group(1)), match.group(2)
        if "$" in title:
            raise SubjectError(f"{label}: Lesson {number}: titles cannot contain placeholders (goals can).")
        if number in seen:
            raise SubjectError(f"{label}: Lesson {number} appears twice.")
        seen.add(number)
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        goal = next((g.group(1) for line in lines[index + 1:end] if (g := GOAL_LINE.match(line))), None)
        if goal is None:
            raise SubjectError(f"{label}: Lesson {number} has no '**Goal:**' line (mastery is judged against it).")
        think = next((t.group(1) for line in lines[index + 1:end] if (t := THINK_LINE.match(line))), None)
        if think is not None and len(think) > THINK_MAX_CHARS:
            raise SubjectError(f"{label}: Lesson {number}: the 'Think about' line is {len(think)} characters; keep it under {THINK_MAX_CHARS}.")
        lessons.append(Lesson(f"{unit_id}.{number}", number, title, goal, unit_id, think))
    return tuple(lessons)


def _read_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as err:
        raise SubjectError(f"{path}: not valid TOML: {err}") from None


def _text(meta: dict, key: str, label: str) -> str:
    value = meta.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SubjectError(f"{label}: '{key}' must be a non-empty string.")
    return value


def _string_list(meta: dict, key: str, label: str, *, allow_empty: bool) -> list[str]:
    value = meta.get(key, [] if allow_empty else None)
    ok = isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value) and (value or allow_empty)
    if not ok:
        raise SubjectError(f"{label}: '{key}' must be a {'list' if allow_empty else 'non-empty list'} of strings.")
    return value

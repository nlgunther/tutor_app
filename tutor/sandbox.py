"""Build a child's sandbox folder from templates, the subject pack and the child's profile.

Layout (everything is generated except sessions/ and codes.json, which are never overwritten):

    <home>/sandboxes/<child>[-rehearsal]/
        SKILL.md  start_prompt.md  tutor_sandbox.pyz  codes.json
        units/<unit>.md        recreated on every build, so a removed unit never lingers
        sessions/              the tutor session writes its logs here

Example:
    dest = render_sandbox(home, profile, subject, rehearsal=False, now=datetime.now())
"""
import shutil
import tempfile
import zipapp
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from string import Template

from tutor.errors import SandboxError
from tutor.ledger import start_facts
from tutor.paths import PACKAGE_DATA, REHEARSAL_SUFFIX, Home, write_text
from tutor.profiles import CHILD_ID, ChildProfile
from tutor.sessionlog import INITIATORS, SessionLoad, load_sessions, session_id_for
from tutor.subjects import PICTURES_DIR, Lesson, Subject

SKILL_FILE = "SKILL.md"
START_PROMPT_FILE = "start_prompt.md"
RUNTIME_FILE = "tutor_sandbox.pyz"
UNITS_DIR = "units"
SESSIONS_DIR = "sessions"
TEMPLATES_DIR = PACKAGE_DATA / "templates"
# The only modules that may enter a sandbox. A test checks they import nothing else from tutor.
RUNTIME_MODULES = ("__init__.py", "errors.py", "codes.py", "sandbox_runtime.py")
RUNTIME_ENTRY = "tutor.sandbox_runtime:run"


def base_context(profile: ChildProfile, subject: Subject) -> dict[str, str]:
    """Every placeholder the templates and unit files may use."""
    he, him, his = profile.pronouns
    return {
        "child_id": profile.child_id, "name": profile.name, "description": profile.description,
        "age": str(profile.age), "he": he, "him": him, "his": his, "He": he.capitalize(),
        "reading_level": profile.reading_level, "bridges": profile.bridges,
        "adjacent_per_session": str(profile.adjacent_per_session),
        "adjacent_per_week": str(profile.adjacent_per_week),
        "subject_id": subject.subject_id, "subject_title": subject.title, "scope_in": subject.scope_in,
        "adjacent_examples": subject.adjacent_examples, "bridge_map": "; ".join(subject.bridge_map),
        "greeting": subject.greeting, "start_prompt_file": START_PROMPT_FILE,
        "runtime_file": RUNTIME_FILE, "units_dir": UNITS_DIR, "pictures_dir": PICTURES_DIR,
    }


def render_text(text: str, context: Mapping[str, str], label: str) -> str:
    """Substitute ${placeholders}; an unknown placeholder or stray $ is an error, never left in the text."""
    try:
        return Template(text).substitute(context)
    except KeyError as err:
        raise SandboxError(f"{label}: unknown placeholder ${{{err.args[0]}}}.") from None
    except ValueError as err:
        raise SandboxError(f"{label}: bad placeholder syntax ({err}); write $$ for a literal dollar sign.") from None


def render_start_prompt(
    profile: ChildProfile, subject: Subject, load: SessionLoad, now: datetime, initiated_by: str
) -> str:
    """Fill the briefing template from the profile, the subject and the sessions so far."""
    if initiated_by not in INITIATORS:
        raise SandboxError(f"initiated_by must be one of {INITIATORS}, got {initiated_by!r}.")
    facts = start_facts(load.records, subject, now)
    context = base_context(profile, subject)
    context |= {
        "session_id": session_id_for(profile.child_id, now),
        "when": f"{now:%A %Y-%m-%d %H:%M}",
        "initiated_by": initiated_by,
        "week_adjacent_used": str(facts.week_adjacent_used),
        "previous_notes": " ".join(facts.previous_notes.split()),  # one line, so notes cannot restructure the briefing
        "next_lesson": _describe_next(facts.remaining, context),
        "course_files": ", ".join(f"`{UNITS_DIR}/{unit.unit_id}.md`" for unit in subject.units),
    }
    template = (TEMPLATES_DIR / START_PROMPT_FILE).read_text(encoding="utf-8")
    return render_text(template, context, START_PROMPT_FILE)


def _describe_next(remaining: tuple[Lesson, ...], context: Mapping[str, str]) -> str:
    if not remaining:
        return "none: every lesson is mastered. Ask the parent which topic to revisit."
    lesson = remaining[0]
    goal = render_text(lesson.goal, context, f"goal of {lesson.lesson_id}")  # goals may use ${name}
    return f"{lesson.lesson_id} {lesson.title} (goal: {goal})"


def render_sandbox(home: Home, profile: ChildProfile, subject: Subject, *, rehearsal: bool, now: datetime) -> Path:
    """Create or refresh the sandbox. Everything is rendered before anything is written, so a bad
    template leaves an existing sandbox untouched."""
    dest = home.sandbox_dir(profile.child_id, rehearsal)
    context = base_context(profile, subject)
    skill = render_text((TEMPLATES_DIR / SKILL_FILE).read_text(encoding="utf-8"), context, SKILL_FILE)
    units = {f"{unit.unit_id}.md": render_text(unit.body, context, f"unit {unit.unit_id}") for unit in subject.units}
    sessions = dest / SESSIONS_DIR
    load = load_sessions(sessions) if sessions.is_dir() else SessionLoad((), ())
    prompt = render_start_prompt(profile, subject, load, now, "parent")

    sessions.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(dest / UNITS_DIR, ignore_errors=True)
    (dest / UNITS_DIR).mkdir()
    for name, text in units.items():
        write_text(dest / UNITS_DIR / name, text)
    shutil.rmtree(dest / PICTURES_DIR, ignore_errors=True)  # a refresh must not keep pictures the pack dropped
    if subject.pictures:
        (dest / PICTURES_DIR).mkdir()
        for picture in subject.pictures:
            shutil.copyfile(picture, dest / PICTURES_DIR / picture.name)
    write_text(dest / SKILL_FILE, skill)
    write_text(dest / START_PROMPT_FILE, prompt)
    build_runtime(dest / RUNTIME_FILE)
    return dest


def write_start_prompt(
    dest: Path, profile: ChildProfile, subject: Subject, now: datetime, initiated_by: str
) -> SessionLoad:
    """Refresh start_prompt.md from the sessions recorded so far. Returns what it read."""
    load = load_sessions(dest / SESSIONS_DIR)
    write_text(dest / START_PROMPT_FILE, render_start_prompt(profile, subject, load, now, initiated_by))
    return load


def build_runtime(target: Path) -> None:
    """Zip the restricted runtime (verify-only) into one file the session can run."""
    source = Path(__file__).parent
    with tempfile.TemporaryDirectory() as staging:
        package = Path(staging) / "tutor"
        package.mkdir()
        for name in RUNTIME_MODULES:
            shutil.copyfile(source / name, package / name)
        zipapp.create_archive(staging, target, main=RUNTIME_ENTRY, compressed=True)


def require_sandbox(home: Home, child_id: str, rehearsal: bool) -> Path:
    """Return the sandbox folder, or say which command creates it."""
    dest = home.sandbox_dir(child_id, rehearsal)
    if not (dest / SKILL_FILE).is_file():
        flag = " --rehearsal" if rehearsal else ""
        raise SandboxError(f"No sandbox for {child_id!r} at {dest}. Run `tutor sandbox {child_id}{flag}` first.")
    return dest


def delete_sandbox(home: Home, child_id: str, rehearsal: bool) -> None:
    """Delete one sandbox folder with everything in it (sessions, codes, files).

    Refuses any id that is not a valid child id (so '..' or a path can never point outside the
    sandboxes folder), however the caller got it. A folder that does not exist is left alone."""
    folder = home.sandbox_dir(child_id, rehearsal)
    if not CHILD_ID.match(child_id) or folder.parent != home.sandboxes_dir:
        raise SandboxError(f"Refusing to delete {folder}: not a sandbox folder of this home.")
    if not folder.exists():
        return
    try:
        shutil.rmtree(folder)
    except OSError as err:
        raise SandboxError(
            f"Could not delete {folder} ({err}). Close the chat and any File Explorer window showing it, then try again."
        ) from None

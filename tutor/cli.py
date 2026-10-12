"""Command-line interface: thin glue that parses arguments and calls the domain modules.

Every handler returns the text to print. Expected failures are TutorErrors and print as one line.

Example:
    tutor init
    tutor child add "David" --description "a precocious 10-year-old"
    tutor sandbox david
    tutor codes new david --count 20 --out ..\\david_codes.txt
    tutor start david
    tutor review david
    tutor reset david --confirm david
"""
import argparse
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from tutor.codes import CODES_FILE, new_codes, status
from tutor.errors import CodeError, LogError, SandboxError, TutorError
from tutor.paths import Home, create_home, find_home
from tutor.profiles import ChildProfile, add_profile, list_children, load_profile
from tutor.report import render_digest
from tutor.sandbox import SESSIONS_DIR, delete_sandbox, render_sandbox, require_sandbox, write_start_prompt
from tutor.sessionlog import INITIATORS, load_sessions, select_session
from tutor.subjects import Subject, load_subject
from tutor.transcript import delete_rehearsal_transcripts, save_transcript

DEFAULT_CODE_COUNT = 20
REHEARSAL_CODE_COUNT = 5
PASTE_MESSAGE = "\\startChildSession\nRead start_prompt.md and SKILL.md in this folder and follow them."


@dataclass(frozen=True)
class Runtime:
    """What a handler needs from the outside world; tests pass fixed values."""
    explicit_home: str | None
    env: Mapping[str, str]
    cwd: Path
    now: datetime

    def home(self) -> Home:
        return find_home(self.explicit_home, self.env, self.cwd)


@dataclass(frozen=True)
class Loaded:
    """A child's profile and subject, loaded together."""
    home: Home
    profile: ChildProfile
    subject: Subject


def _load(args: argparse.Namespace, runtime: Runtime) -> Loaded:
    home = runtime.home()
    profile = load_profile(home, args.child)
    return Loaded(home, profile, load_subject(home, profile.subject))


def _codes_line(dest: Path, name: str) -> str:
    path = dest / CODES_FILE
    if not path.exists():
        return f"No exit codes yet: run `tutor codes new {name} --count {DEFAULT_CODE_COUNT} --out <file outside the sandbox>`."
    code_status = status(path)
    return f"{code_status.remaining} of {code_status.issued} exit codes left."


def _paste_block(dest: Path) -> str:
    return f"Connect this folder in the Claude desktop app:\n  {dest}\nThen paste this into a new chat:\n\n{PASTE_MESSAGE}"


def _init(args, runtime: Runtime) -> str:
    home = create_home(Path(args.folder).resolve())
    return f"Created tutor home at {home.root}\nNext: tutor child add \"Name\" --description \"...\"  (run from inside that folder)"


def _child_add(args, runtime: Runtime) -> str:
    home = runtime.home()
    given = {"age": args.age, "bridges": args.bridges, "subject": args.subject,
             "target_minutes_per_week": args.target_minutes, "target_concepts_per_week": args.target_concepts}
    overrides = {key: value for key, value in given.items() if value is not None}
    if args.pronouns:
        overrides["pronouns"] = args.pronouns
    profile = add_profile(home, args.name, args.description, overrides)
    return f"Wrote {home.children_dir / (profile.child_id + '.toml')}\nNext: tutor sandbox {profile.child_id}"


def _child_list(args, runtime: Runtime) -> str:
    home = runtime.home()
    rows = [load_profile(home, child_id) for child_id in list_children(home)]
    return "\n".join(f"{p.child_id}: {p.name}, {p.subject}" for p in rows) or "No children yet: tutor child add"


def _sandbox(args, runtime: Runtime) -> str:
    loaded = _load(args, runtime)
    dest = render_sandbox(loaded.home, loaded.profile, loaded.subject, rehearsal=args.rehearsal, now=runtime.now)
    return f"Sandbox ready: {dest}\n{_codes_line(dest, args.child)}"


def _codes_new(args, runtime: Runtime) -> str:
    home = runtime.home()
    dest = require_sandbox(home, args.child, args.rehearsal)
    out = _checked_output_path(home, args.out, args.rehearsal)
    count = args.count if args.count is not None else (REHEARSAL_CODE_COUNT if args.rehearsal else DEFAULT_CODE_COUNT)
    codes = new_codes(dest / CODES_FILE, count, replace=args.replace)
    if out is None:
        return "Rehearsal codes (throwaway):\n" + "\n".join(codes)
    try:
        with out.open("x", encoding="utf-8") as handle:
            handle.write("\n".join(codes) + "\n")
    except OSError as err:
        raise CodeError(f"The codes were created but {out} could not be written ({err}). Run again with --replace.") from None
    return f"Wrote {count} codes to {out}. Print it, keep it away from {args.child}, and delete the file when done."


def _checked_output_path(home: Home, out: str | None, rehearsal: bool) -> Path | None:
    """Validate the paper-list path before any code is created, so a bad path never costs a batch."""
    if out is None:
        if not rehearsal:
            raise CodeError("--out FILE is required: codes for a real sandbox are never printed to the screen.")
        return None
    path = Path(out)
    if home.is_inside_a_sandbox(path):
        raise CodeError(f"{path} is inside a sandbox, where the tutor session could read it. Choose a folder outside {home.sandboxes_dir}.")
    if path.exists():
        raise CodeError(f"{path} already exists; choose a new file name.")
    if not path.resolve().parent.is_dir():
        raise CodeError(f"The folder for {path} does not exist.")
    return path


def _codes_status(args, runtime: Runtime) -> str:
    dest = require_sandbox(runtime.home(), args.child, args.rehearsal)
    return _codes_line(dest, args.child)


def _start(args, runtime: Runtime) -> str:
    loaded = _load(args, runtime)
    dest = require_sandbox(loaded.home, args.child, args.rehearsal)
    load = write_start_prompt(dest, loaded.profile, loaded.subject, runtime.now, args.initiated_by)
    notes = []
    if load.records and not load.records[-1].finished:
        notes.append(f"Note: the last session ({load.records[-1].session_id}) was never ended with an exit code.")
    if not (dest / CODES_FILE).exists() or status(dest / CODES_FILE).remaining == 0:
        notes.append("Warning: no exit codes left. Create some first: tutor codes new " + args.child)
    return "\n".join([_paste_block(dest)] + notes)


def _review(args, runtime: Runtime) -> str:
    loaded = _load(args, runtime)
    dest = require_sandbox(loaded.home, args.child, args.rehearsal)
    load = load_sessions(dest / SESSIONS_DIR)
    digest = render_digest(loaded.profile, loaded.subject, load, runtime.now, args.session)
    record = select_session(load.records, args.session) if load.records else None
    asked_in_chat = bool(record and record.summary and record.summary.save_transcript)
    if not (args.save_transcript or asked_in_chat):
        return digest
    if record is None:
        raise LogError("--saveTranscript: there is no session to save yet.")
    saved = save_transcript(loaded.home, loaded.profile, loaded.subject, record, args.rehearsal)
    return f"{digest}\nTranscript saved: {saved}"


def _rehearsal(args, runtime: Runtime) -> str:
    return _create_rehearsal(_load(args, runtime), args.child, runtime)


def _create_rehearsal(loaded: Loaded, child: str, runtime: Runtime) -> str:
    dest = render_sandbox(loaded.home, loaded.profile, loaded.subject, rehearsal=True, now=runtime.now)
    lines = [f"Rehearsal sandbox ready: {dest}"]
    if not (dest / CODES_FILE).exists():
        codes = new_codes(dest / CODES_FILE, REHEARSAL_CODE_COUNT, replace=True)
        lines.append("Rehearsal codes (throwaway):\n" + "\n".join(codes))
    else:
        lines.append(_codes_line(dest, child))
    return "\n".join(lines + ["", _paste_block(dest)])


def _require_confirmation(args, dest: Path, action: str) -> None:
    """A real sandbox holds the only copy of the logs and codes, so destroying it needs the child's id repeated."""
    if args.rehearsal or args.confirm == args.child:
        return
    sessions = len(list((dest / SESSIONS_DIR).glob("*.md")))
    codes = status(dest / CODES_FILE) if (dest / CODES_FILE).exists() else None
    held = f"{sessions} session log(s) and " + (f"{codes.remaining} of {codes.issued} unused codes" if codes else "no codes")
    wrong = f" (you gave {args.confirm!r})" if args.confirm else ""
    raise SandboxError(
        f"This would permanently {action} {args.child}'s REAL sandbox, erasing {held}. Transcripts already saved in "
        f"HIL_transcripts are kept. To go ahead, repeat the child's id: tutor {args.command} {args.child} --confirm {args.child}{wrong}"
    )


def _delete(args, runtime: Runtime) -> str:
    home = runtime.home()
    dest = require_sandbox(home, args.child, args.rehearsal)
    _require_confirmation(args, dest, "delete")
    delete_sandbox(home, args.child, args.rehearsal)
    if not args.rehearsal:
        return f"Deleted {args.child}'s sandbox. Saved transcripts in {home.transcripts_dir} were kept. Rebuild with: tutor sandbox {args.child}"
    removed = delete_rehearsal_transcripts(home, args.child)
    return f"Deleted {args.child}'s rehearsal sandbox and {removed} saved rehearsal transcript(s)."


def _reset(args, runtime: Runtime) -> str:
    loaded = _load(args, runtime)
    if args.rehearsal:
        delete_sandbox(loaded.home, args.child, rehearsal=True)
        delete_rehearsal_transcripts(loaded.home, args.child)
        return "Rehearsal reset to factory state.\n" + _create_rehearsal(loaded, args.child, runtime)
    dest = require_sandbox(loaded.home, args.child, rehearsal=False)
    _require_confirmation(args, dest, "reset")
    delete_sandbox(loaded.home, args.child, rehearsal=False)
    dest = render_sandbox(loaded.home, loaded.profile, loaded.subject, rehearsal=False, now=runtime.now)
    return (f"Reset {args.child}'s sandbox to factory state at {dest}: session logs and codes erased, other files rebuilt "
            f"from the current profile, defaults and subject. Saved transcripts were kept.\n"
            f"Next: tutor codes new {args.child} --count {DEFAULT_CODE_COUNT} --out <file outside the sandbox>")


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for every command."""
    parser = argparse.ArgumentParser(prog="tutor", description="Parent-gated tutoring sandboxes for Claude.")
    parser.add_argument("--home", help="tutor home folder (default: $TUTOR_HOME, else the nearest folder above here with tutor.toml)")
    commands = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("child", help="child id, e.g. adam")
    common.add_argument("--rehearsal", action="store_true", help="use the child's rehearsal sandbox (adult dry runs)")

    init = commands.add_parser("init", help="create a tutor home")
    init.set_defaults(handler=_init)
    init.add_argument("folder", nargs="?", default=".", help="folder to create (default: here)")
    _add_child_commands(commands)
    commands.add_parser("sandbox", parents=[common], help="create or refresh a sandbox").set_defaults(handler=_sandbox)
    _add_code_commands(commands, common)
    _add_session_commands(commands, common)
    _add_destructive_commands(commands, common)
    return parser


def _add_child_commands(commands) -> None:
    child = commands.add_parser("child", help="manage child profiles").add_subparsers(dest="action", required=True)
    add = child.add_parser("add", help="create children/<id>.toml")
    add.set_defaults(handler=_child_add)
    add.add_argument("name")
    add.add_argument("--description", required=True, help='for example "a precocious 10-year-old who loves Roblox"')
    add.add_argument("--age", type=int)
    add.add_argument("--bridges")
    add.add_argument("--subject")
    add.add_argument("--pronouns", nargs=3, metavar=("SUBJECT", "OBJECT", "POSSESSIVE"))
    add.add_argument("--target-minutes", type=float, help="m0 in the S metric")
    add.add_argument("--target-concepts", type=float, help="c0 in the S metric")
    child.add_parser("list", help="list children").set_defaults(handler=_child_list)


def _add_code_commands(commands, common) -> None:
    codes = commands.add_parser("codes", help="exit codes").add_subparsers(dest="action", required=True)
    new = codes.add_parser("new", parents=[common], help="create a batch of one-time codes")
    new.set_defaults(handler=_codes_new)
    new.add_argument("--count", type=int, help=f"default {DEFAULT_CODE_COUNT} ({REHEARSAL_CODE_COUNT} for rehearsal)")
    new.add_argument("--out", help="file for the paper list; must be outside every sandbox")
    new.add_argument("--replace", action="store_true", help="invalidate unused codes from an earlier batch")
    codes.add_parser("status", parents=[common], help="how many codes are left").set_defaults(handler=_codes_status)


def _add_session_commands(commands, common) -> None:
    start = commands.add_parser("start", parents=[common], help="prepare the briefing and print what to paste")
    start.set_defaults(handler=_start)
    start.add_argument("--initiated-by", choices=INITIATORS, default="parent", help="who asked for this session")
    review = commands.add_parser("review", parents=[common], help="digest of the latest session and the week")
    review.set_defaults(handler=_review)
    review.add_argument("--session", help="a session id instead of the latest")
    review.add_argument("--saveTranscript", dest="save_transcript", action="store_true",
                        help="also save a readable transcript in HIL_transcripts (done automatically when the exit command carried --saveTranscript)")
    rehearsal = commands.add_parser("rehearsal", help="set up an adult dry run for a child")
    rehearsal.set_defaults(handler=_rehearsal)
    rehearsal.add_argument("child")


def _add_destructive_commands(commands, common) -> None:
    confirm = argparse.ArgumentParser(add_help=False)
    confirm.add_argument("--confirm", help="repeat the child's id to confirm an action on a REAL sandbox (rehearsals need no confirmation)")
    delete = commands.add_parser("delete", parents=[common, confirm], help="delete a sandbox (a rehearsal also loses its saved transcripts)")
    delete.set_defaults(handler=_delete)
    reset = commands.add_parser("reset", parents=[common, confirm], help="reset a sandbox to factory state: erase sessions and codes, rebuild files")
    reset.set_defaults(handler=_reset)


def main(
    argv: list[str] | None = None, *, now: datetime | None = None,
    env: Mapping[str, str] | None = None, cwd: Path | None = None,
) -> int:
    """Run one command; returns the exit status (0 ok, 1 expected failure)."""
    args = build_parser().parse_args(argv)
    runtime = Runtime(args.home, os.environ if env is None else env, cwd or Path.cwd(), now or datetime.now())
    try:
        output = args.handler(args, runtime)
    except TutorError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    print(output)
    return 0


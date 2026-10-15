"""Tests for tutor.cli: every command, its output, and the errors a parent can hit."""
import os
from datetime import datetime
from pathlib import Path

import pytest

from tutor import cli
from tutor.codes import CODES_FILE, status, verify_and_consume
from tutor.errors import SandboxError
from tutor.paths import ENV_VAR, create_home
from tutor.profiles import load_profile

FINISHED = ('ended_by = "code"', 'mastered = ["forces.0"]', 'notes = "Resume at forces.1."')


@pytest.fixture
def run(capsys, now):
    """Run the CLI in-process: run(*argv, home=..., cwd=..., env=...) -> (exit status, stdout, stderr)."""

    def runner(*argv, home=None, cwd=Path("/"), env=None):
        prefix = ["--home", str(home.root)] if home else []
        status_code = cli.main([*prefix, *argv], now=now, env={} if env is None else env, cwd=cwd)
        captured = capsys.readouterr()
        return status_code, captured.out, captured.err

    return runner


def test_init_creates_a_home(run, tmp_path):
    code, out, _ = run("init", str(tmp_path / "h"))
    assert code == 0 and "Created tutor home" in out and (tmp_path / "h" / "tutor.toml").is_file()


def test_init_twice_is_an_error(run, tmp_path):
    run("init", str(tmp_path / "h"))
    code, out, err = run("init", str(tmp_path / "h"))
    assert (code, out) == (1, "") and "already a tutor home" in err


def test_init_defaults_to_the_current_folder(run, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert run("init")[0] == 0 and (tmp_path / "tutor.toml").is_file()


def test_child_add_and_list(run, home):
    assert run("child", "list", home=home)[1].startswith("No children yet")
    code, out, _ = run("child", "add", "David", "--description", "a kid", home=home)
    assert code == 0 and "david.toml" in out and "tutor sandbox david" in out
    assert run("child", "list", home=home)[1].strip() == "david: David, physics"


def test_child_add_with_every_option(run, home):
    run("child", "add", "Sam", "--description", "x", "--age", "12", "--bridges", "chess", "--subject", "physics",
        "--pronouns", "she", "her", "her", "--target-minutes", "60", "--target-concepts", "3", home=home)
    profile = load_profile(home, "sam")
    assert (profile.age, profile.bridges, profile.pronouns) == (12, "chess", ("she", "her", "her"))
    assert profile.targets_set


def test_child_add_errors(run, home):
    run("child", "add", "Sam", "--description", "x", home=home)
    assert "already exists" in run("child", "add", "Sam", "--description", "x", home=home)[2]
    assert "between 3 and 17" in run("child", "add", "Kid", "--description", "x", "--age", "40", home=home)[2]


def test_sandbox_command(run, home, adam):
    code, out, _ = run("sandbox", "adam", home=home)
    assert code == 0 and "Sandbox ready" in out and "No exit codes yet" in out
    assert (home.sandbox_dir("adam") / "SKILL.md").is_file()


def test_sandbox_for_an_unknown_child(run, home):
    code, _, err = run("sandbox", "nobody", home=home)
    assert code == 1 and "No profile for 'nobody'" in err


def test_sandbox_with_an_unknown_subject(run, home):
    run("child", "add", "Sam", "--description", "x", "--subject", "chemistry", home=home)
    assert "No subject 'chemistry'" in run("sandbox", "sam", home=home)[2]


def test_codes_new_requires_a_sandbox(run, home, adam, tmp_path):
    code, _, err = run("codes", "new", "adam", "--out", str(tmp_path / "p.txt"), home=home)
    assert code == 1 and "tutor sandbox adam" in err


def test_codes_new_writes_a_paper_list_that_works(run, home, sandbox, tmp_path):
    paper = tmp_path / "paper.txt"
    code, out, _ = run("codes", "new", "adam", "--count", "2", "--out", str(paper), home=home)
    assert code == 0 and "Wrote 2 codes" in out
    listed = paper.read_text(encoding="utf-8").split()
    assert len(listed) == 2 and listed[0] not in out
    assert verify_and_consume(sandbox / CODES_FILE, listed[0]) is True


def test_codes_new_default_count(run, home, sandbox, tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "DEFAULT_CODE_COUNT", 3)
    run("codes", "new", "adam", "--out", str(tmp_path / "p.txt"), home=home)
    assert status(sandbox / CODES_FILE).issued == 3


def test_real_sandbox_codes_are_never_printed(run, home, sandbox):
    code, out, err = run("codes", "new", "adam", home=home)
    assert code == 1 and out == "" and "--out FILE is required" in err
    assert not (sandbox / CODES_FILE).exists()


def test_paper_list_inside_a_sandbox_is_refused_before_any_code_is_made(run, home, sandbox):
    code, _, err = run("codes", "new", "adam", "--out", str(sandbox / "units" / "paper.txt"), home=home)
    assert code == 1 and "inside a sandbox" in err
    assert not (sandbox / CODES_FILE).exists()


def test_paper_list_that_already_exists_is_refused(run, home, sandbox, tmp_path):
    (tmp_path / "p.txt").write_text("keep me", encoding="utf-8")
    assert "already exists" in run("codes", "new", "adam", "--out", str(tmp_path / "p.txt"), home=home)[2]
    assert (tmp_path / "p.txt").read_text(encoding="utf-8") == "keep me"
    assert not (sandbox / CODES_FILE).exists()


def test_paper_list_in_a_missing_folder_is_refused(run, home, sandbox, tmp_path):
    assert "does not exist" in run("codes", "new", "adam", "--out", str(tmp_path / "nodir" / "p.txt"), home=home)[2]
    assert not (sandbox / CODES_FILE).exists()


def test_a_second_batch_needs_replace_and_the_first_survives(run, home, sandbox, tmp_path):
    run("codes", "new", "adam", "--count", "2", "--out", str(tmp_path / "a.txt"), home=home)
    code, _, err = run("codes", "new", "adam", "--count", "2", "--out", str(tmp_path / "b.txt"), home=home)
    assert code == 1 and "--replace" in err and not (tmp_path / "b.txt").exists()
    first = (tmp_path / "a.txt").read_text(encoding="utf-8").split()
    assert run("codes", "new", "adam", "--count", "2", "--replace", "--out", str(tmp_path / "b.txt"), home=home)[0] == 0
    assert verify_and_consume(sandbox / CODES_FILE, first[0]) is False


def test_write_failure_after_creation_tells_the_parent_how_to_recover(run, home, sandbox, tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "_checked_output_path", lambda *args: tmp_path / "gone" / "p.txt")
    code, _, err = run("codes", "new", "adam", "--count", "1", "--out", "ignored", home=home)
    assert code == 1 and "could not be written" in err and "--replace" in err


def test_rehearsal_codes_are_printed_and_default_to_five(run, home, adam, physics, now):
    run("sandbox", "adam", "--rehearsal", home=home)
    code, out, _ = run("codes", "new", "adam", "--rehearsal", home=home)
    assert code == 0 and out.startswith("Rehearsal codes (throwaway):")
    assert len(out.split()[3:]) == 5


def test_codes_status(run, home, sandbox, tmp_path):
    assert "No exit codes yet" in run("codes", "status", "adam", home=home)[1]
    run("codes", "new", "adam", "--count", "2", "--out", str(tmp_path / "p.txt"), home=home)
    assert run("codes", "status", "adam", home=home)[1].strip() == "2 of 2 exit codes left."


def test_start_prints_what_to_paste_and_refreshes_the_briefing(run, home, sandbox, tmp_path):
    run("codes", "new", "adam", "--count", "1", "--out", str(tmp_path / "p.txt"), home=home)
    code, out, _ = run("start", "adam", "--initiated-by", "child", home=home)
    assert code == 0 and str(sandbox) in out
    assert "\\startChildSession\nRead start_prompt.md and SKILL.md" in out and "Warning" not in out
    assert "Initiated by: child" in (sandbox / "start_prompt.md").read_text(encoding="utf-8")


def test_start_warns_when_no_codes_remain(run, home, sandbox):
    assert "no exit codes left" in run("start", "adam", home=home)[1]


def test_start_warns_about_an_unfinished_previous_session(run, home, sandbox, make_session):
    make_session(sandbox / "sessions")
    assert "was never ended with an exit code" in run("start", "adam", home=home)[1]


def test_start_rejects_an_unknown_initiator(run, home, sandbox):
    with pytest.raises(SystemExit) as raised:
        run("start", "adam", "--initiated-by", "robot", home=home)
    assert raised.value.code == 2


def test_review_without_a_sandbox(run, home, adam):
    assert "tutor sandbox adam" in run("review", "adam", home=home)[2]


def test_review_with_no_sessions_then_with_one(run, home, sandbox, make_session):
    assert "No sessions recorded yet." in run("review", "adam", home=home)[1]
    make_session(sandbox / "sessions", summary=FINISHED)
    out = run("review", "adam", home=home)[1]
    assert "Session 2026-10-11_0900_adam" in out and "Resume at forces.1." in out


def test_review_of_a_named_session(run, home, sandbox, make_session):
    make_session(sandbox / "sessions", stamp="2026-10-06_0900")
    make_session(sandbox / "sessions", stamp="2026-10-09_0900")
    assert "Session 2026-10-06_0900_adam" in run("review", "adam", "--session", "2026-10-06_0900_adam", home=home)[1]
    assert "No session 'x'" in run("review", "adam", "--session", "x", home=home)[2]


def test_rehearsal_setup_and_reuse(run, home, adam):
    code, out, _ = run("rehearsal", "adam", home=home)
    rehearsal = home.sandbox_dir("adam", rehearsal=True)
    assert code == 0 and rehearsal.is_dir() and "Rehearsal codes (throwaway)" in out and str(rehearsal) in out
    assert status(rehearsal / CODES_FILE).remaining == 5

    out = run("rehearsal", "adam", home=home)[1]  # second time: nothing is regenerated
    assert "Rehearsal codes" not in out and "5 of 5 exit codes left." in out



def test_rehearsal_never_touches_the_real_sandbox(run, home, sandbox, make_session, tmp_path):
    run("codes", "new", "adam", "--count", "1", "--out", str(tmp_path / "p.txt"), home=home)
    make_session(sandbox / "sessions")
    codes_before = (sandbox / CODES_FILE).read_bytes()
    run("rehearsal", "adam", home=home)
    run("reset", "adam", "--rehearsal", home=home)
    assert (sandbox / CODES_FILE).read_bytes() == codes_before
    assert len(list((sandbox / "sessions").iterdir())) == 1
    rehearsal = home.sandbox_dir("adam", rehearsal=True)
    make_session(rehearsal / "sessions", stamp="2026-10-10_0900")
    assert "2026-10-10_0900" not in run("review", "adam", home=home)[1]  # real review ignores rehearsal logs
    assert "2026-10-10_0900" in run("review", "adam", "--rehearsal", home=home)[1]


def test_home_found_from_environment_and_from_the_working_folder(run, home, adam):
    assert run("child", "list", env={ENV_VAR: str(home.root)})[1].startswith("adam")
    assert run("child", "list", cwd=home.children_dir)[1].startswith("adam")


def test_no_home_is_a_clear_error(run, tmp_path):
    code, out, err = run("child", "list", cwd=tmp_path)
    assert (code, out) == (1, "") and "No tutor home found" in err


def test_a_command_is_required():
    with pytest.raises(SystemExit) as raised:
        cli.build_parser().parse_args([])
    assert raised.value.code == 2


def test_two_homes_do_not_interfere(run, tmp_path):
    first, second = create_home(tmp_path / "one"), create_home(tmp_path / "two")
    run("child", "add", "Adam", "--description", "x", home=first)
    assert run("child", "list", home=second)[1].startswith("No children yet")


def test_review_does_not_save_a_transcript_unless_asked(run, home, sandbox, make_session):
    make_session(sandbox / "sessions", summary=FINISHED)
    out = run("review", "adam", home=home)[1]
    assert "Transcript saved" not in out and not home.transcripts_dir.exists()


def test_review_saves_a_transcript_with_the_flag(run, home, sandbox, make_session):
    make_session(sandbox / "sessions", summary=FINISHED)
    out = run("review", "adam", "--saveTranscript", home=home)[1]
    saved = home.transcripts_dir / "2026-10-11_0900_adam.md"
    assert f"Transcript saved: {saved}" in out and "**Adam** (turn 1): let's start" in saved.read_text(encoding="utf-8")


def test_review_saves_a_transcript_when_the_exit_command_asked_for_one(run, home, sandbox, make_session):
    make_session(sandbox / "sessions", summary=(*FINISHED, "save_transcript = true"))
    assert "Transcript saved" in run("review", "adam", home=home)[1]


def test_review_saves_the_named_session(run, home, sandbox, make_session):
    make_session(sandbox / "sessions", stamp="2026-10-06_0900")
    make_session(sandbox / "sessions", stamp="2026-10-09_0900")
    run("review", "adam", "--session", "2026-10-06_0900_adam", "--saveTranscript", home=home)
    assert [p.name for p in home.transcripts_dir.iterdir()] == ["2026-10-06_0900_adam.md"]


def test_rehearsal_review_saves_into_the_rehearsal_folder(run, home, adam, make_session):
    run("rehearsal", "adam", home=home)
    make_session(home.sandbox_dir("adam", rehearsal=True) / "sessions", summary=FINISHED)
    run("review", "adam", "--rehearsal", "--saveTranscript", home=home)
    assert (home.transcripts_dir / "rehearsal" / "2026-10-11_0900_adam.md").is_file()


def test_saving_with_no_sessions_is_an_error(run, home, sandbox):
    code, _, err = run("review", "adam", "--saveTranscript", home=home)
    assert code == 1 and "no session to save" in err and not home.transcripts_dir.exists()


@pytest.fixture
def lived_in(run, home, sandbox, make_session, tmp_path):
    """A real sandbox with codes, a session and a saved transcript, plus a rehearsal with the same."""
    run("codes", "new", "adam", "--count", "2", "--out", str(tmp_path / "paper.txt"), home=home)
    make_session(sandbox / "sessions", summary=FINISHED)
    run("review", "adam", "--saveTranscript", home=home)
    run("rehearsal", "adam", home=home)
    rehearsal = home.sandbox_dir("adam", rehearsal=True)
    make_session(rehearsal / "sessions", summary=FINISHED)
    run("review", "adam", "--rehearsal", "--saveTranscript", "--save-session", home=home)
    return sandbox, rehearsal


REAL_TRANSCRIPT = "2026-10-11_0900_adam.md"


def test_deleting_a_rehearsal_needs_no_confirmation_and_takes_its_transcripts(run, home, lived_in):
    sandbox, rehearsal = lived_in
    code, out, _ = run("delete", "adam", "--rehearsal", home=home)
    assert code == 0 and "Deleted adam's rehearsal sandbox and 1 saved rehearsal transcript(s)." in out
    assert not rehearsal.exists() and sandbox.exists()
    assert not (home.transcripts_dir / "rehearsal" / REAL_TRANSCRIPT).exists()
    assert (home.transcripts_dir / REAL_TRANSCRIPT).is_file()


def test_deleting_a_real_sandbox_without_confirmation_changes_nothing_and_says_what_is_at_stake(run, home, lived_in):
    sandbox, _ = lived_in
    code, out, err = run("delete", "adam", home=home)
    assert (code, out) == (1, "")
    assert "REAL sandbox" in err and "1 session log(s) and 2 of 2 unused codes" in err
    assert "tutor delete adam --confirm adam" in err and "Transcripts already saved" in err
    assert sandbox.exists()


def test_a_wrong_confirmation_is_refused_and_named(run, home, lived_in):
    sandbox, _ = lived_in
    code, _, err = run("delete", "adam", "--confirm", "david", home=home)
    assert code == 1 and "you gave 'david'" in err and sandbox.exists()


def test_confirmed_deletion_of_a_real_sandbox_keeps_its_transcripts(run, home, lived_in):
    sandbox, rehearsal = lived_in
    code, out, _ = run("delete", "adam", "--confirm", "adam", home=home)
    assert code == 0 and "Deleted adam's sandbox" in out and "tutor sandbox adam" in out
    assert not sandbox.exists() and rehearsal.exists()
    assert (home.transcripts_dir / REAL_TRANSCRIPT).is_file()
    assert (home.transcripts_dir / "rehearsal" / REAL_TRANSCRIPT).is_file()


def test_deleting_what_does_not_exist_says_how_to_create_it(run, home, adam):
    assert "tutor sandbox adam --rehearsal" in run("delete", "adam", "--rehearsal", home=home)[2]


def test_reset_of_a_real_sandbox_returns_it_to_factory_state(run, home, lived_in):
    sandbox, _ = lived_in
    (sandbox / "SKILL.md").write_text("tampered", encoding="utf-8")
    assert run("reset", "adam", home=home)[0] == 1 and (sandbox / "SKILL.md").read_text(encoding="utf-8") == "tampered"
    code, out, _ = run("reset", "adam", "--confirm", "adam", home=home)
    assert code == 0 and "factory state" in out and "tutor codes new adam" in out
    assert list((sandbox / "sessions").iterdir()) == [] and not (sandbox / CODES_FILE).exists()
    assert (sandbox / "SKILL.md").read_text(encoding="utf-8").startswith("---\nname: adam-physics-sandbox")
    assert (sandbox / "tutor_sandbox.pyz").is_file() and (sandbox / "diagrams").is_dir()
    assert (home.transcripts_dir / REAL_TRANSCRIPT).is_file()


def test_reset_of_a_rehearsal_gives_a_fresh_sandbox_with_new_codes_and_no_transcripts(run, home, lived_in):
    sandbox, rehearsal = lived_in
    old_codes = (rehearsal / CODES_FILE).read_bytes()
    code, out, _ = run("reset", "adam", "--rehearsal", home=home)
    assert code == 0 and "Rehearsal reset to factory state." in out and "Rehearsal codes (throwaway)" in out
    assert list((rehearsal / "sessions").iterdir()) == [] and (rehearsal / CODES_FILE).read_bytes() != old_codes
    assert status(rehearsal / CODES_FILE).remaining == 5
    assert not (home.transcripts_dir / "rehearsal" / REAL_TRANSCRIPT).exists()
    assert len(list((sandbox / "sessions").iterdir())) == 1 and status(sandbox / CODES_FILE).remaining == 2


def test_reset_of_a_rehearsal_that_does_not_exist_simply_creates_it(run, home, adam):
    code, out, _ = run("reset", "adam", "--rehearsal", home=home)
    assert code == 0 and home.sandbox_dir("adam", rehearsal=True).is_dir() and "Rehearsal codes" in out


def test_reset_of_a_missing_real_sandbox_says_how_to_create_it(run, home, adam):
    assert "tutor sandbox adam" in run("reset", "adam", "--confirm", "adam", home=home)[2]


def _finished_rehearsal(run, home, make_session):
    run("rehearsal", "adam", home=home)
    rehearsal = home.sandbox_dir("adam", rehearsal=True)
    make_session(rehearsal / "sessions", summary=FINISHED)
    return rehearsal


def test_reviewing_a_finished_dry_run_deletes_it_but_keeps_its_transcript(run, home, adam, make_session):
    rehearsal = _finished_rehearsal(run, home, make_session)
    code, out, _ = run("review", "adam", "--rehearsal", "--saveTranscript", home=home)
    assert code == 0 and "Dry run deleted" in out and "Transcript saved" in out
    assert not rehearsal.exists()
    assert (home.transcripts_dir / "rehearsal" / "2026-10-11_0900_adam.md").is_file()


def test_save_session_keeps_the_dry_run(run, home, adam, make_session):
    rehearsal = _finished_rehearsal(run, home, make_session)
    code, out, _ = run("review", "adam", "--rehearsal", "--save-session", home=home)
    assert code == 0 and "Dry run kept (--save-session)" in out and rehearsal.is_dir()


def test_an_unfinished_dry_run_is_never_auto_deleted(run, home, adam, make_session):
    run("rehearsal", "adam", home=home)
    rehearsal = home.sandbox_dir("adam", rehearsal=True)
    make_session(rehearsal / "sessions")
    out = run("review", "adam", "--rehearsal", home=home)[1]
    assert "not ended with an exit code" in out and rehearsal.is_dir()


def test_a_dry_run_with_no_session_is_kept(run, home, adam):
    run("rehearsal", "adam", home=home)
    out = run("review", "adam", "--rehearsal", home=home)[1]
    assert "no session yet" in out and home.sandbox_dir("adam", rehearsal=True).is_dir()


def test_save_session_without_rehearsal_is_an_error(run, home, sandbox, make_session):
    make_session(sandbox / "sessions", summary=FINISHED)
    code, _, err = run("review", "adam", "--save-session", home=home)
    assert code == 1 and "only applies to a dry run" in err


def test_a_real_review_never_deletes_the_real_sandbox(run, home, sandbox, make_session):
    make_session(sandbox / "sessions", summary=FINISHED)
    run("review", "adam", home=home)
    assert sandbox.is_dir() and len(list((sandbox / "sessions").iterdir())) == 1


def test_a_failed_auto_delete_keeps_the_digest_and_says_why(run, home, adam, make_session, monkeypatch):
    _finished_rehearsal(run, home, make_session)

    def locked(*_, **__):
        raise SandboxError("Could not delete (locked). Close the chat and retry.")

    monkeypatch.setattr("tutor.cli.delete_sandbox", locked)
    code, out, _ = run("review", "adam", "--rehearsal", home=home)
    assert code == 0 and "Rehearsal not deleted: Could not delete" in out and "adam" in out


def test_deleting_an_already_auto_deleted_dry_run_clears_leftover_transcripts(run, home, adam, make_session):
    _finished_rehearsal(run, home, make_session)
    run("review", "adam", "--rehearsal", "--saveTranscript", home=home)
    code, out, _ = run("delete", "adam", "--rehearsal", home=home)
    assert code == 0 and "already deleted" in out and "Removed 1 saved" in out
    assert not list((home.transcripts_dir / "rehearsal").iterdir())


def test_review_warns_when_the_latest_code_was_never_marked_used(run, home, sandbox, make_session, tmp_path):
    run("codes", "new", "adam", "--count", "2", "--out", str(tmp_path / "paper.txt"), home=home)
    make_session(sandbox / "sessions", summary=FINISHED)  # started 2026-10-11 09:00
    old = datetime(2026, 10, 10, 12, 0).timestamp()
    os.utime(sandbox / CODES_FILE, (old, old))  # codes.json untouched since before the session
    assert "may not be marked as used" in run("review", "adam", home=home)[1]
    recent = datetime(2026, 10, 11, 9, 30).timestamp()
    os.utime(sandbox / CODES_FILE, (recent, recent))  # a spend rewrote it during the session
    assert "may not be marked as used" not in run("review", "adam", home=home)[1]

"""End-to-end: real subprocesses, the real tutor_sandbox.pyz, and a tutor session simulated by writing its log.

These tests cover what unit tests cannot: that the installed command line, the generated files and the
zipped runtime work together the way a parent and the child's session will use them.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
LOG = """\
1 | child | IN_SCOPE | - | - | let's start
2 | tutor | - | forces.0 | no | Quick warm-up: what is acceleration?
3 | child | ADJACENT | forces.0 | - | why is the sky blue
4 | tutor | - | forces.0 | no | Light scatters.
5 | child | OFF_TOPIC | forces.0 | - | give me robux
6 | tutor | - | forces.0 | yes | I can't, but how does a jump work?
7 | parent | - | - | - | \\endChildSession [code redacted]
<!-- summary:begin -->
ended_by = "code"
initiated_by = "child"
mastered = ["forces.0"]
notes = "Great on acceleration; resume at forces.1."
open_questions = []
<!-- summary:end -->
"""


def tutor(*argv, cwd, env=None):
    environment = {**os.environ, "PYTHONPATH": str(ROOT), **(env or {})}
    return subprocess.run([sys.executable, "-m", "tutor", *argv], cwd=cwd, env=environment,
                          capture_output=True, text=True, timeout=120)


def pyz(sandbox, *argv, cwd):
    return subprocess.run([sys.executable, str(sandbox / "tutor_sandbox.pyz"), *argv], cwd=cwd,
                          capture_output=True, text=True, timeout=120)


def make_home(tmp_path, count="2"):
    home = tmp_path / "home"
    assert tutor("init", str(home), cwd=tmp_path).returncode == 0
    assert tutor("child", "add", "Adam", "--description", "a precocious 10-year-old", cwd=home).returncode == 0
    assert tutor("sandbox", "adam", cwd=home).returncode == 0
    paper = tmp_path / "paper.txt"
    assert tutor("codes", "new", "adam", "--count", count, "--out", str(paper), cwd=home).returncode == 0
    return home, home / "sandboxes" / "adam", paper.read_text(encoding="utf-8").split()


def test_a_whole_cycle_from_setup_to_the_next_briefing(tmp_path):
    home, sandbox, codes = make_home(tmp_path)

    started = tutor("start", "adam", "--initiated-by", "child", cwd=home)
    assert started.returncode == 0 and "\\startChildSession" in started.stdout
    session_id = re.search(r"Session id: (\S+)", (sandbox / "start_prompt.md").read_text(encoding="utf-8")).group(1)

    # The child's session verifies the exit code through the shipped archive, from another folder.
    assert pyz(sandbox, "verify", "AAAAAAAAAAAA", cwd=tmp_path).stdout.strip() == "NO"
    ended = pyz(sandbox, "verify", codes[0], cwd=tmp_path)
    assert (ended.returncode, ended.stdout.strip()) == (0, "OK")
    assert pyz(sandbox, "verify", codes[0], cwd=tmp_path).stdout.strip() == "NO"  # spent

    (sandbox / "sessions" / f"{session_id}.md").write_text(LOG, encoding="utf-8")
    digest = tutor("review", "adam", cwd=home).stdout
    assert f"Session {session_id}" in digest and "initiated by child" in digest
    assert "Ended: with an exit code" in digest and "Mastered: forces.0 Acceleration" in digest
    assert "Adjacent questions: 1 this session; 1 of 7 this week" in digest
    assert 'turn 6: "give me robux"' in digest and "Safety flags: none" in digest
    assert "Warnings" not in digest
    assert "Next: forces.1" in digest

    saved = tutor("review", "adam", "--saveTranscript", cwd=home)
    transcript = home / "HIL_transcripts" / f"{session_id}.md"
    assert saved.returncode == 0 and f"Transcript saved: {transcript}" in saved.stdout
    assert "**Adam** (turn 1)" in transcript.read_text(encoding="utf-8") and codes[0] not in transcript.read_text(encoding="utf-8")

    tutor("start", "adam", cwd=home)
    briefing = (sandbox / "start_prompt.md").read_text(encoding="utf-8")
    assert "resume at forces.1." in briefing and "Next lesson: forces.1 Force" in briefing
    assert "already used this week: 1 of 7" in briefing
    assert codes[0] not in (sandbox / "sessions" / f"{session_id}.md").read_text(encoding="utf-8")


def test_the_session_runtime_can_only_verify(tmp_path):
    home, sandbox, codes = make_home(tmp_path)
    before = (sandbox / "codes.json").read_bytes()
    for attempt in (["codes", "new"], ["generate", "5"], ["status"], []):
        assert pyz(sandbox, *attempt, cwd=tmp_path).returncode == 2
    assert (sandbox / "codes.json").read_bytes() == before


def test_the_runtime_reports_a_missing_store_as_an_error_not_a_refusal(tmp_path):
    home, sandbox, codes = make_home(tmp_path)
    (sandbox / "codes.json").unlink()
    result = pyz(sandbox, "verify", codes[0], cwd=tmp_path)
    assert result.returncode == 2 and "ERROR" in result.stderr and result.stdout == ""


def test_a_refreshed_sandbox_keeps_working_codes_and_logs(tmp_path):
    home, sandbox, codes = make_home(tmp_path)
    (sandbox / "sessions" / "2026-10-06_0900_adam.md").write_text(LOG, encoding="utf-8")
    assert tutor("sandbox", "adam", cwd=home).returncode == 0
    assert pyz(sandbox, "verify", codes[1], cwd=tmp_path).stdout.strip() == "OK"
    assert (sandbox / "sessions" / "2026-10-06_0900_adam.md").exists()


def test_home_from_the_environment_and_a_second_child_isolated_from_the_first(tmp_path):
    home, adam_sandbox, adam_codes = make_home(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    env = {"TUTOR_HOME": str(home)}
    assert tutor("child", "add", "David", "--description", "a precocious 10-year-old", cwd=elsewhere, env=env).returncode == 0
    assert tutor("sandbox", "david", cwd=elsewhere, env=env).returncode == 0
    david = home / "sandboxes" / "david"
    paper = tmp_path / "david_codes.txt"
    assert tutor("codes", "new", "david", "--count", "1", "--out", str(paper), cwd=elsewhere, env=env).returncode == 0
    david_code = paper.read_text(encoding="utf-8").split()[0]

    assert pyz(david, "verify", adam_codes[0], cwd=tmp_path).stdout.strip() == "NO"  # Adam's code is no use to David
    assert pyz(david, "verify", david_code, cwd=tmp_path).stdout.strip() == "OK"
    texts = "\n".join(p.read_text(encoding="utf-8") for p in david.rglob("*.md"))
    assert "Adam" not in texts
    assert "David" not in "\n".join(p.read_text(encoding="utf-8") for p in adam_sandbox.rglob("*.md"))


def test_a_rehearsal_runs_without_touching_the_real_sandbox(tmp_path):
    home, sandbox, codes = make_home(tmp_path)
    result = tutor("rehearsal", "adam", cwd=home)
    assert result.returncode == 0
    rehearsal = home / "sandboxes" / "adam-rehearsal"
    rehearsal_code = result.stdout.split("(throwaway):")[1].split()[0]
    assert pyz(rehearsal, "verify", rehearsal_code, cwd=tmp_path).stdout.strip() == "OK"
    assert pyz(sandbox, "verify", rehearsal_code, cwd=tmp_path).stdout.strip() == "NO"
    assert pyz(sandbox, "verify", codes[0], cwd=tmp_path).stdout.strip() == "OK"


def test_errors_are_one_line_on_stderr_with_status_1(tmp_path):
    result = tutor("review", "adam", cwd=tmp_path)
    assert result.returncode == 1 and result.stdout == ""
    assert result.stderr.startswith("error: No tutor home found") and "Traceback" not in result.stderr


def test_a_dry_run_from_creation_to_deletion(tmp_path):
    home, sandbox, _ = make_home(tmp_path)
    created = tutor("rehearsal", "adam", cwd=home)
    rehearsal = home / "sandboxes" / "adam-rehearsal"
    code = created.stdout.split("(throwaway):")[1].split()[0]
    assert pyz(rehearsal, "verify", code, cwd=tmp_path).stdout.strip() == "OK"

    (rehearsal / "sessions" / "2026-10-11_0900_adam.md").write_text(LOG, encoding="utf-8")
    saved = tutor("review", "adam", "--rehearsal", "--saveTranscript", cwd=home)
    assert saved.returncode == 0 and (home / "HIL_transcripts" / "rehearsal" / "2026-10-11_0900_adam.md").is_file()

    removed = tutor("delete", "adam", "--rehearsal", cwd=home)
    assert removed.returncode == 0 and not rehearsal.exists()
    assert not list((home / "HIL_transcripts" / "rehearsal").iterdir()) and sandbox.is_dir()

    refused = tutor("delete", "adam", cwd=home)
    assert refused.returncode == 1 and "--confirm adam" in refused.stderr and sandbox.is_dir()

"""Tests for tutor.transcript: the readable copy of a session kept in HIL_transcripts."""
from tutor.sessionlog import parse_session
from tutor.transcript import delete_rehearsal_transcripts, render_transcript, save_transcript

TURNS = (
    "1 | child | IN_SCOPE | - | - | let's start",
    "2 | tutor | - | forces.0 | no | Quick warm-up: what is acceleration?",
    "3 | child | OFF_TOPIC | forces.0 | - | can you make me a portal into Roblox",
    "4 | tutor | - | forces.0 | yes | I can't do that. How does a jump work?",
    "5 | parent | - | - | - | \\endChildSession [code redacted] --saveTranscript",
)
SUMMARY = ('ended_by = "code"', 'mastered = ["forces.0"]', 'notes = "Liked the jump."', "save_transcript = true")


def record_for(make_session, tmp_path, summary=SUMMARY, lines=TURNS):
    return parse_session(make_session(tmp_path, lines=list(lines), summary=summary))


def test_every_turn_appears_in_order_with_speaker_and_tags(make_session, tmp_path, adam, physics):
    text = render_transcript(adam, physics, record_for(make_session, tmp_path))
    lines = [line for line in text.splitlines() if line.startswith("**")]
    assert lines == [
        "**Adam** (turn 1): let's start",
        "**Claude** (turn 2): Quick warm-up: what is acceleration?",
        "**Adam** (turn 3, OFF_TOPIC): can you make me a portal into Roblox",
        "**Claude** (turn 4, redirected): I can't do that. How does a jump work?",
        "**Parent** (turn 5): \\endChildSession [code redacted] --saveTranscript",
    ]


def test_header_and_footer_summarise_the_session(make_session, tmp_path, adam, physics):
    text = render_transcript(adam, physics, record_for(make_session, tmp_path))
    assert text.startswith("# Adam: tutoring session, 2026-10-11 09:00")
    assert "ended with an exit code" in text and "Mastered: forces.0 Acceleration" in text
    assert "Notes for next time: Liked the jump." in text


def test_an_unfinished_session_says_so_and_has_no_notes(make_session, tmp_path, adam, physics):
    text = render_transcript(adam, physics, record_for(make_session, tmp_path, summary=None))
    assert "NOT with an exit code" in text and "Notes for next time" not in text


def test_log_warnings_are_carried_into_the_transcript(make_session, tmp_path, adam, physics):
    bad = (*TURNS[:1], "3 | tutor | - | - | no | skipped a number")
    text = render_transcript(adam, physics, record_for(make_session, tmp_path, lines=bad))
    assert "Warnings:" in text and "expected number 2" in text


def test_save_writes_one_file_named_for_the_session(make_session, tmp_path, home, adam, physics):
    record = record_for(make_session, tmp_path)
    path = save_transcript(home, adam, physics, record, rehearsal=False)
    assert path == home.transcripts_dir / "2026-10-11_0900_adam.md"
    assert path.read_text(encoding="utf-8") == render_transcript(adam, physics, record)


def test_rehearsal_transcripts_are_kept_apart(make_session, tmp_path, home, adam, physics):
    path = save_transcript(home, adam, physics, record_for(make_session, tmp_path), rehearsal=True)
    assert path.parent == home.transcripts_dir / "rehearsal"


def test_saving_twice_replaces_the_file(make_session, tmp_path, home, adam, physics):
    record = record_for(make_session, tmp_path)
    first = save_transcript(home, adam, physics, record, rehearsal=False)
    assert save_transcript(home, adam, physics, record, rehearsal=False) == first
    assert len(list(home.transcripts_dir.iterdir())) == 1


def test_the_transcripts_folder_is_outside_every_sandbox(home):
    assert not home.is_inside_a_sandbox(home.transcripts_dir)


def test_deleting_rehearsal_transcripts_touches_only_that_childs_rehearsal_files(make_session, tmp_path, home, adam, physics):
    mine = save_transcript(home, adam, physics, record_for(make_session, tmp_path), rehearsal=True)
    real = save_transcript(home, adam, physics, record_for(make_session, tmp_path), rehearsal=False)
    longer_name = home.transcripts_dir / "rehearsal" / "2026-10-11_0900_mary_adam.md"  # ends with _adam.md but is another child
    other = home.transcripts_dir / "rehearsal" / "2026-10-11_0900_david.md"
    longer_name.write_text("x", encoding="utf-8")
    other.write_text("x", encoding="utf-8")
    assert delete_rehearsal_transcripts(home, "adam") == 1
    assert not mine.exists() and real.exists() and longer_name.exists() and other.exists()


def test_deleting_rehearsal_transcripts_when_there_are_none(home):
    assert delete_rehearsal_transcripts(home, "adam") == 0

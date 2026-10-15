"""Shared fixtures. Every test gets a fresh home inside tmp_path; nothing touches the real filesystem.

Fixtures: no_real_tutor_home (autouse), now, summary_ok, home, adam, physics, sandbox, make_session.
"""
import os
from datetime import datetime, timedelta

import pytest

from tutor.paths import ENV_VAR, create_home
from tutor.profiles import add_profile
from tutor.sandbox import render_sandbox
from tutor.subjects import load_subject

NOW = datetime(2026, 10, 11, 9, 15)  # a Sunday; its ISO week starts Monday 2026-10-05
ADAM_DESCRIPTION = "a precocious 10-year-old who loves Roblox"
DEFAULT_TURNS = (
    "1 | child | IN_SCOPE | - | - | let's start",
    "2 | tutor | - | - | no | Hello!",
)
SUMMARY_OK = (
    'ended_by = "code"',
    'initiated_by = "parent"',
    'mastered = ["forces.0"]',
    'notes = "Fast on acceleration."',
    'open_questions = ["why is the sky blue"]',
)


@pytest.fixture(autouse=True)
def no_real_tutor_home(monkeypatch):
    """A parent who exports TUTOR_HOME would otherwise point every command (including subprocesses) at the real home."""
    monkeypatch.delenv(ENV_VAR, raising=False)


@pytest.fixture
def summary_ok():
    return SUMMARY_OK


@pytest.fixture
def now():
    return NOW


@pytest.fixture
def home(tmp_path):
    return create_home(tmp_path / "home")


@pytest.fixture
def adam(home):
    return add_profile(home, "Adam", ADAM_DESCRIPTION, {"bridges": "Roblox, soccer and cooking"})


@pytest.fixture
def physics(home):
    return load_subject(home, "physics")


@pytest.fixture
def sandbox(home, adam, physics, now):
    return render_sandbox(home, adam, physics, rehearsal=False, now=now)


@pytest.fixture
def make_session():
    """Factory: write a session log with a chosen start stamp and a file mtime `minutes` later."""

    def make(folder, stamp="2026-10-11_0900", child="adam", lines=None, summary=None, minutes=30):
        path = folder / f"{stamp}_{child}.md"
        body = list(DEFAULT_TURNS if lines is None else lines)
        if summary is not None:
            body += ["<!-- summary:begin -->", *summary, "<!-- summary:end -->"]
        path.write_text("\n".join(body) + "\n", encoding="utf-8")
        started = datetime.strptime(stamp, "%Y-%m-%d_%H%M")
        mtime = (started + timedelta(minutes=minutes)).timestamp()
        os.utime(path, (mtime, mtime))
        return path

    return make


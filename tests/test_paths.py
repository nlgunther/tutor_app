"""Tests for tutor.paths: creating and locating a home, and the sandbox path rules."""
import os
from pathlib import Path

import pytest

from tutor.errors import HomeError
from tutor.paths import ENV_VAR, create_home, find_home


def test_create_home_builds_expected_layout(tmp_path):
    home = create_home(tmp_path / "h")
    assert home.marker_path.read_text() == "schema_version = 1\n"
    assert home.defaults_path.is_file()
    assert all(folder.is_dir() for folder in (home.children_dir, home.subjects_dir, home.sandboxes_dir))


def test_create_home_refuses_an_existing_home(home):
    with pytest.raises(HomeError, match="already"):
        create_home(home.root)


def test_find_home_explicit(home):
    assert find_home(str(home.root), {}, Path("/nowhere")) == home


def test_explicit_home_without_marker_fails(tmp_path):
    with pytest.raises(HomeError, match="tutor init"):
        find_home(str(tmp_path), {}, tmp_path)


def test_explicit_beats_environment(home, tmp_path):
    other = create_home(tmp_path / "other")
    assert find_home(str(home.root), {ENV_VAR: str(other.root)}, tmp_path) == home


def test_environment_used_without_explicit(home, tmp_path):
    assert find_home(None, {ENV_VAR: str(home.root)}, tmp_path) == home


def test_environment_without_marker_fails(tmp_path):
    with pytest.raises(HomeError, match=ENV_VAR):
        find_home(None, {ENV_VAR: str(tmp_path)}, tmp_path)


def test_nearest_ancestor_with_marker_is_found(home):
    assert find_home(None, {}, home.children_dir) == home


def test_no_home_anywhere_explains_how_to_create_one(tmp_path):
    with pytest.raises(HomeError, match="tutor init"):
        find_home(None, {}, tmp_path)


def test_sandbox_dir_names(home):
    assert home.sandbox_dir("adam") == home.sandboxes_dir / "adam"
    assert home.sandbox_dir("adam", rehearsal=True) == home.sandboxes_dir / "adam-rehearsal"


def test_is_inside_a_sandbox(home):
    assert home.is_inside_a_sandbox(home.sandboxes_dir / "adam" / "notes.txt")
    assert home.is_inside_a_sandbox(home.sandboxes_dir / "never-built" / "x")  # would be inside
    assert not home.is_inside_a_sandbox(home.root / "codes.txt")


def test_dotdot_is_resolved_before_checking(home):
    assert not home.is_inside_a_sandbox(home.sandboxes_dir / ".." / "codes.txt")
    assert home.is_inside_a_sandbox(home.root / "children" / ".." / "sandboxes" / "adam" / "x")


def test_a_home_without_its_empty_folders_still_works(home, adam, now):
    """Empty folders vanish when a home is copied as files, so the code must recreate them."""
    from tutor.sandbox import render_sandbox
    from tutor.subjects import load_subject, available_subjects

    home.subjects_dir.rmdir()
    home.sandboxes_dir.rmdir()
    assert "physics" in available_subjects(home)
    built = render_sandbox(home, adam, load_subject(home, "physics"), rehearsal=False, now=now)
    assert (built / "SKILL.md").is_file()


def test_tests_never_see_a_real_tutor_home():
    assert ENV_VAR not in os.environ  # the autouse fixture in conftest.py removed it, even if the parent exported one

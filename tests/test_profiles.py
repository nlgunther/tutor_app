"""Tests for tutor.profiles: ids, defaults merging, validation of every field, writing profiles."""
import pytest

from tutor.errors import ProfileError
from tutor.profiles import FIELDS, add_profile, list_children, load_profile, slugify


def write_child(home, body, name="kid"):
    (home.children_dir / f"{name}.toml").write_text(body, encoding="utf-8")


@pytest.mark.parametrize("name, expected", [("David", "david"), ("  Mary-Ann ", "maryann"), ("Zoë", "zo"), ("A_1", "a_1")])
def test_slugify(name, expected):
    assert slugify(name) == expected


@pytest.mark.parametrize("name", ["", "   ", "123", "!!!", "_x"])
def test_slugify_rejects_unusable_names(name):
    with pytest.raises(ProfileError, match="child id"):
        slugify(name)


def test_add_profile_writes_only_what_differs_from_defaults(home):
    add_profile(home, "David", "a kid", {"bridges": "soccer"})
    text = (home.children_dir / "david.toml").read_text(encoding="utf-8")
    assert text == 'name = "David"\ndescription = "a kid"\nbridges = "soccer"\n'


def test_loaded_profile_merges_defaults(home):
    add_profile(home, "David", "a kid")
    profile = load_profile(home, "david")
    assert (profile.name, profile.age, profile.subject) == ("David", 10, "physics")
    assert profile.pronouns == ("he", "him", "his")
    assert (profile.adjacent_per_session, profile.adjacent_per_week) == (3, 7)
    assert profile.target_minutes_per_week is None and not profile.targets_set


def test_add_profile_returns_the_validated_profile(home):
    assert add_profile(home, "Adam", "x").child_id == "adam"


def test_special_characters_survive_a_round_trip(home):
    description = 'He said "hi" — ünï \\ ok'
    add_profile(home, "Adam", description)
    assert load_profile(home, "adam").description == description


def test_add_profile_refuses_to_overwrite(home):
    add_profile(home, "Adam", "x")
    with pytest.raises(ProfileError, match="already exists"):
        add_profile(home, "Adam", "y")


def test_invalid_override_is_rejected_and_nothing_is_written(home):
    with pytest.raises(ProfileError, match="between 3 and 17"):
        add_profile(home, "Adam", "x", {"age": 40})
    assert not (home.children_dir / "adam.toml").exists()


def test_overrides_with_targets_and_pronouns(home):
    add_profile(home, "Sam", "x", {"pronouns": ["she", "her", "her"], "target_minutes_per_week": 60, "target_concepts_per_week": 2.5})
    profile = load_profile(home, "sam")
    assert profile.pronouns == ("she", "her", "her")
    assert profile.targets_set


def test_one_target_alone_does_not_enable_targets(home):
    add_profile(home, "Sam", "x", {"target_minutes_per_week": 60})
    assert not load_profile(home, "sam").targets_set


@pytest.mark.parametrize("extra, message", [
    ("age = 2", "between 3 and 17"),
    ("age = 18", "between 3 and 17"),
    ('age = "ten"', "invalid value"),
    ("age = true", "invalid value"),
    ("age = 9.5", "invalid value"),
    ('pronouns = ["he", "him"]', "invalid value"),
    ('pronouns = ["he", "him", ""]', "invalid value"),
    ("adjacent_per_session = -1", "between"),
    ("adjacent_per_week = 1.5", "invalid value"),
    ("target_minutes_per_week = 0", "between"),
    ('target_minutes_per_week = "x"', "invalid value"),
    ("target_concepts_per_week = 0", "between"),
    ('flavor = "odd"', "unknown fields"),
])
def test_invalid_field_values_fail(home, extra, message):
    write_child(home, f'name = "K"\ndescription = "d"\n{extra}\n')
    with pytest.raises(ProfileError, match=message):
        load_profile(home, "kid")


def test_blank_name_fails(home):
    write_child(home, 'name = "  "\ndescription = "d"\n')
    with pytest.raises(ProfileError, match="name"):
        load_profile(home, "kid")


def test_missing_required_field_fails(home):
    write_child(home, 'name = "K"\n')
    with pytest.raises(ProfileError, match="missing fields .*description"):
        load_profile(home, "kid")


def test_invalid_toml_fails(home):
    write_child(home, "name = \n")
    with pytest.raises(ProfileError, match="not valid TOML"):
        load_profile(home, "kid")


def test_missing_defaults_file_points_to_init(home):
    add_profile(home, "Adam", "x")
    home.defaults_path.unlink()
    with pytest.raises(ProfileError, match="tutor init"):
        load_profile(home, "adam")


def test_unknown_child_lists_known_children(home):
    add_profile(home, "Adam", "x")
    with pytest.raises(ProfileError, match=r"No profile for 'bob'.*\['adam'\]"):
        load_profile(home, "bob")


def test_unknown_child_with_no_children_says_none(home):
    with pytest.raises(ProfileError, match="none"):
        load_profile(home, "bob")


def test_file_name_that_is_not_a_valid_id_fails(home):
    write_child(home, 'name = "K"\ndescription = "d"\n', name="Bad-Name")
    with pytest.raises(ProfileError, match="not a valid child id"):
        load_profile(home, "Bad-Name")


def test_list_children_is_sorted(home):
    for name in ("Zed", "Adam", "Mia"):
        add_profile(home, name, "x")
    assert list_children(home) == ["adam", "mia", "zed"]


def test_every_default_field_is_a_known_field(home):
    import tomllib
    defaults = tomllib.loads(home.defaults_path.read_text(encoding="utf-8"))
    assert defaults.keys() <= FIELDS.keys()

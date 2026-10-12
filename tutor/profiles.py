"""Child profiles: one TOML file per child in <home>/children/, merged over <home>/defaults.toml.

Example (children/david.toml):
    name = "David"
    description = "a precocious 10-year-old who used to love Roblox"
    bridges = "soccer, cooking and everyday objects"

Every other field comes from defaults.toml. Unknown or invalid fields are errors, never ignored.
"""
import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from tutor.errors import ProfileError
from tutor.paths import Home

CHILD_ID = re.compile(r"^[a-z][a-z0-9_]{0,31}$")


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_pronouns(value) -> bool:
    return isinstance(value, list) and len(value) == 3 and all(_is_text(item) for item in value)


# field -> (type check, required, allowed range or None). Single source of truth for validation.
FIELDS = {
    "name": (_is_text, True, None),
    "description": (_is_text, True, None),
    "age": (_is_int, True, (3, 17)),
    "pronouns": (_is_pronouns, True, None),
    "reading_level": (_is_text, True, None),
    "bridges": (_is_text, True, None),
    "subject": (_is_text, True, None),
    "adjacent_per_session": (_is_int, True, (0, 50)),
    "adjacent_per_week": (_is_int, True, (0, 500)),
    "target_minutes_per_week": (_is_number, False, (1, 10_000)),
    "target_concepts_per_week": (_is_number, False, (0.1, 1_000)),
}


@dataclass(frozen=True)
class ChildProfile:
    """A validated child profile: the family defaults merged with the child's own file."""
    child_id: str
    name: str
    description: str
    age: int
    pronouns: tuple[str, str, str]  # subject, object, possessive: ("he", "him", "his")
    reading_level: str
    bridges: str
    subject: str
    adjacent_per_session: int
    adjacent_per_week: int
    target_minutes_per_week: float | None = None  # m0 in S = (m/m0)^2 + (c/c0)^2; None until you set it
    target_concepts_per_week: float | None = None  # c0

    @property
    def targets_set(self) -> bool:
        return self.target_minutes_per_week is not None and self.target_concepts_per_week is not None


def slugify(name: str) -> str:
    """'David' -> 'david'. Raises ProfileError if no valid id can be made."""
    child_id = re.sub(r"[^a-z0-9_]", "", name.strip().lower())
    if not CHILD_ID.match(child_id):
        raise ProfileError(f"Cannot make a child id from {name!r}: use letters, digits or _, starting with a letter.")
    return child_id


def list_children(home: Home) -> list[str]:
    """Child ids that have a profile, sorted."""
    return sorted(path.stem for path in home.children_dir.glob("*.toml"))


def load_profile(home: Home, child_id: str) -> ChildProfile:
    """Load and validate children/<child_id>.toml merged over the defaults."""
    path = home.children_dir / f"{child_id}.toml"
    if not path.is_file():
        raise ProfileError(f"No profile for {child_id!r} (expected {path}). Known children: {list_children(home) or 'none'}.")
    return _build(child_id, _read_toml(home.defaults_path) | _read_toml(path), path.name)


def add_profile(home: Home, name: str, description: str, overrides: dict | None = None) -> ChildProfile:
    """Write children/<id>.toml containing only what differs from the defaults. Refuses to overwrite."""
    child_id = slugify(name)
    path = home.children_dir / f"{child_id}.toml"
    if path.exists():
        raise ProfileError(f"{path} already exists; edit it directly.")
    own = {"name": name, "description": description} | (overrides or {})
    profile = _build(child_id, _read_toml(home.defaults_path) | own, path.name)  # validate before writing
    path.write_text("".join(f"{key} = {_toml_value(value)}\n" for key, value in own.items()), encoding="utf-8")
    return profile


def _toml_value(value) -> str:
    return json.dumps(value, ensure_ascii=False)  # JSON strings, numbers and arrays are valid TOML


def _read_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ProfileError(f"Missing {path}. Run `tutor init` to create the home.") from None
    except tomllib.TOMLDecodeError as err:
        raise ProfileError(f"{path.name} is not valid TOML: {err}") from None


def _build(child_id: str, raw: dict, source: str) -> ChildProfile:
    if not CHILD_ID.match(child_id):
        raise ProfileError(f"{source}: {child_id!r} is not a valid child id.")
    unknown = sorted(raw.keys() - FIELDS.keys())
    missing = sorted(key for key, (_, required, _) in FIELDS.items() if required and key not in raw)
    if unknown or missing:
        raise ProfileError(f"{source}: unknown fields {unknown}, missing fields {missing}.")
    for key, value in raw.items():
        check, _, bounds = FIELDS[key]
        if not check(value):
            raise ProfileError(f"{source}: {key} has an invalid value {value!r}.")
        if bounds and not bounds[0] <= value <= bounds[1]:
            raise ProfileError(f"{source}: {key} must be between {bounds[0]} and {bounds[1]}, got {value}.")
    values = dict(raw, pronouns=tuple(raw["pronouns"]))
    return ChildProfile(child_id=child_id, **values)

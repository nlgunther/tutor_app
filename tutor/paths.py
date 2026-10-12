"""Where things live. A Home is the folder holding tutor.toml, profiles, subjects and sandboxes.

Example:
    home = find_home(None, os.environ, Path.cwd())
    home.sandbox_dir("adam")                 # <home>/sandboxes/adam
    home.sandbox_dir("adam", rehearsal=True) # <home>/sandboxes/adam-rehearsal
"""
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from tutor.errors import HomeError

MARKER = "tutor.toml"
ENV_VAR = "TUTOR_HOME"
SCHEMA_VERSION = 1
PACKAGE_DATA = Path(__file__).parent / "data"
TRANSCRIPTS_DIR = "HIL_transcripts"  # human-in-the-loop copies for the parent; outside every sandbox
REHEARSAL_SUFFIX = "-rehearsal"  # a hyphen cannot occur in a child id, so names never collide


@dataclass(frozen=True)
class Home:
    """The tutor home folder and the paths inside it."""
    root: Path

    @property
    def marker_path(self) -> Path:
        return self.root / MARKER

    @property
    def defaults_path(self) -> Path:
        return self.root / "defaults.toml"

    @property
    def children_dir(self) -> Path:
        return self.root / "children"

    @property
    def subjects_dir(self) -> Path:
        return self.root / "subjects"

    @property
    def sandboxes_dir(self) -> Path:
        return self.root / "sandboxes"

    @property
    def transcripts_dir(self) -> Path:
        return self.root / TRANSCRIPTS_DIR

    def sandbox_dir(self, child_id: str, rehearsal: bool = False) -> Path:
        return self.sandboxes_dir / (child_id + (REHEARSAL_SUFFIX if rehearsal else ""))

    def is_inside_a_sandbox(self, path: Path) -> bool:
        """True if path is, or would be, anywhere under the sandboxes folder (symlinks and .. resolved)."""
        return Path(path).resolve().is_relative_to(self.sandboxes_dir.resolve())


def find_home(explicit: str | None, env: Mapping[str, str], cwd: Path) -> Home:
    """Locate the home: --home, then $TUTOR_HOME, then the nearest folder above cwd that has tutor.toml."""
    if explicit:
        return _require_marker(Path(explicit), "--home")
    if env.get(ENV_VAR):
        return _require_marker(Path(env[ENV_VAR]), ENV_VAR)
    for folder in (cwd, *cwd.parents):
        if (folder / MARKER).is_file():
            return Home(folder)
    raise HomeError(
        f"No tutor home found from {cwd}. Run `tutor init <folder>`, or pass --home / set {ENV_VAR}."
    )


def _require_marker(root: Path, source: str) -> Home:
    if not (root / MARKER).is_file():
        raise HomeError(f"{source} points to {root}, which has no {MARKER}. Run `tutor init {root}` first.")
    return Home(root)


def create_home(root: Path) -> Home:
    """Create a new home with family defaults. Refuses to touch an existing one."""
    home = Home(Path(root))
    if home.marker_path.exists():
        raise HomeError(f"{home.root} is already a tutor home.")
    for folder in (home.children_dir, home.subjects_dir, home.sandboxes_dir):
        folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PACKAGE_DATA / "defaults.toml", home.defaults_path)
    home.marker_path.write_text(f"schema_version = {SCHEMA_VERSION}\n", encoding="utf-8")
    return home


def write_text(path: Path, text: str) -> None:
    """UTF-8 with LF endings on every platform, so files and their hashes are identical everywhere."""
    path.write_text(text, encoding="utf-8", newline="\n")

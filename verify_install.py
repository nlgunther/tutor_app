"""Check that every tracked file matches MANIFEST.txt.

Run from the tutor_app folder:  python verify_install.py
Exit status 0 when every file and the bundle hash match, 1 otherwise.
Hashes ignore line-ending differences, so Windows and Linux copies agree.
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha16(data: bytes) -> str:
    """First 16 hex digits of SHA-256 over CRLF-normalised bytes."""
    return hashlib.sha256(data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")).hexdigest()[:16]


def read_manifest(path: Path) -> tuple[str, dict[str, str]]:
    """Return (bundle hash, {relative path: expected hash}); raises ValueError on a malformed line."""
    bundle, rows = "", {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        key, _, value = line.partition("\t")
        if not value:
            raise ValueError(f"MANIFEST.txt line {number}: expected '<hash><TAB><path>'")
        if key == "bundle:":
            bundle = value
        else:
            rows[value] = key
    return bundle, rows


def main() -> int:
    """Compare every file with the manifest and print a report."""
    bundle, rows = read_manifest(HERE / "MANIFEST.txt")
    problems, actual = [], {}
    for rel, expected in rows.items():
        target = HERE / rel
        if not target.is_file():
            problems.append(f"MISSING   {rel}")
            continue
        actual[rel] = sha16(target.read_bytes())
        if actual[rel] != expected:
            problems.append(f"MODIFIED  {rel}")
    if not problems:
        recomputed = hashlib.sha256("".join(h for _, h in sorted(actual.items())).encode()).hexdigest()[:24]
        if recomputed != bundle:
            problems.append("BUNDLE    hash of hashes does not match")
    for problem in problems:
        print(problem)
    print(f"{len(rows) - len([p for p in problems if p.startswith(('MISSING', 'MODIFIED'))])}/{len(rows)} files verified")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

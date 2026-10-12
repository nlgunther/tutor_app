"""One-time exit codes. Only salted scrypt hashes are stored; plaintext exists once, at generation.

Example:
    codes = new_codes(path, 20)                   # ["K7QF3M9TXA2B", ...]: show once, then discard
    verify_and_consume(path, "k7qf-3m9t-xa2b")    # True, and that code is now spent
    status(path)                                  # CodeStatus(issued=20, remaining=19)

Ships inside tutor_sandbox.pyz, so it may import only the standard library and tutor.errors.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
from dataclasses import dataclass
from pathlib import Path

from tutor.errors import CodeError

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no I, O, 0, 1: unambiguous on paper
CODE_LENGTH = 12  # 32**12 = 2**60 possibilities
MAX_BATCH = 200
SCHEMA = 1
CODES_FILE = "codes.json"  # sits at the sandbox root, next to tutor_sandbox.pyz
CODE_LIKE = re.compile(rf"\b[{ALPHABET}]{{{CODE_LENGTH}}}\b")  # used to spot a leaked code in a log
_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}


@dataclass(frozen=True)
class CodeStatus:
    """How many codes were issued and how many are still unspent."""
    issued: int
    remaining: int


def normalize(code: str) -> str:
    """Ignore case, spaces and dashes: 'k7qf-3m9t xa2b' == 'K7QF3M9TXA2B'."""
    return re.sub(r"[\s-]", "", code).upper()


def new_codes(path: Path, count: int, *, replace: bool = False) -> list[str]:
    """Create a fresh batch. Refuses to discard unused codes unless replace=True."""
    if not 1 <= count <= MAX_BATCH:
        raise CodeError(f"Code count must be between 1 and {MAX_BATCH}, got {count}.")
    if path.exists() and not replace and (left := status(path).remaining):
        raise CodeError(f"{left} unused codes exist at {path}; creating a new batch would invalidate them. Use --replace.")
    codes = ["".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH)) for _ in range(count)]
    entries = [_entry(code) for code in codes]
    _save(path, {"schema": SCHEMA, "issued": count, "entries": entries})
    return codes


def verify_and_consume(path: Path, code: str) -> bool:
    """True if code matches an unspent code; that code is then spent. Wrong codes consume nothing."""
    store = _load(path)
    code = normalize(code)
    if len(code) != CODE_LENGTH or set(code) - set(ALPHABET):  # cheap reject before any scrypt work
        return False
    for position, entry in enumerate(store["entries"]):
        if hmac.compare_digest(_digest(code, bytes.fromhex(entry["salt"])), entry["hash"]):
            del store["entries"][position]
            _save(path, store)
            return True
    return False


def status(path: Path) -> CodeStatus:
    """Report issued and remaining counts without revealing anything about the codes."""
    store = _load(path)
    return CodeStatus(issued=store["issued"], remaining=len(store["entries"]))


def _digest(code: str, salt: bytes) -> str:
    return hashlib.scrypt(code.encode(), salt=salt, **_SCRYPT).hex()


def _entry(code: str) -> dict:
    salt = secrets.token_bytes(16)
    return {"salt": salt.hex(), "hash": _digest(code, salt)}


def _load(path: Path) -> dict:
    try:
        store = json.loads(Path(path).read_text(encoding="utf-8"))
        entries = store["entries"]
        valid = (
            store["schema"] == SCHEMA
            and isinstance(store["issued"], int)
            and all(isinstance(e["salt"], str) and isinstance(e["hash"], str) for e in entries)
        )
        for entry in entries:
            bytes.fromhex(entry["salt"])
    except FileNotFoundError:
        raise CodeError(f"No exit-code file at {path}. Create one with `tutor codes new`.") from None
    except (ValueError, KeyError, TypeError):
        raise CodeError(f"{path} is not a valid exit-code file.") from None
    if not valid:
        raise CodeError(f"{path} is not a valid exit-code file.")
    return store


def _save(path: Path, store: dict) -> None:
    """Write via a temporary file so a crash never leaves a half-written store."""
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(store, indent=1), encoding="utf-8")
    os.replace(temporary, path)

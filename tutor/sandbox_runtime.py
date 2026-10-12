"""Restricted entry point shipped inside each sandbox as tutor_sandbox.pyz.

It can verify and spend one exit code and nothing else: it cannot create, list or reset codes, so a
session that is tricked into running it still cannot mint a code. Imports only tutor.codes and tutor.errors.

Example (run from the sandbox folder):
    python tutor_sandbox.pyz verify K7QF-3M9T-XA2B     # prints OK or NO; exit status 0 or 1
"""
import argparse
import sys
from pathlib import Path

from tutor.codes import CODES_FILE, verify_and_consume
from tutor.errors import CodeError


def main(argv: list[str] | None = None, codes_path: Path | None = None) -> int:
    """Run `verify`; returns 0 for a valid code, 1 for an invalid one, 2 when the store is unusable."""
    parser = argparse.ArgumentParser(prog="tutor_sandbox.pyz", description="Verify a one-time exit code.")
    verify = parser.add_subparsers(dest="command", required=True).add_parser("verify", help="check and spend a code")
    verify.add_argument("code", nargs="+", help="the exit code (spaces and dashes are ignored)")
    args = parser.parse_args(argv)
    path = codes_path or Path(sys.argv[0]).resolve().parent / CODES_FILE
    try:
        accepted = verify_and_consume(path, " ".join(args.code))
    except CodeError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2
    print("OK" if accepted else "NO")
    return 0 if accepted else 1


def run() -> None:
    """Zipapp entry point: zipapp discards main()'s return value, so exit explicitly."""
    sys.exit(main())


if __name__ == "__main__":
    run()

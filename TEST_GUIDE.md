# tutor — Test Suite Reference

Quick reference for adding new tests. Update this file whenever a new test
file is created or a significant pattern changes.

---

## Layout

```
tests/
├── conftest.py               # shared fixtures and the log-writing factory
├── test_paths.py             # locating/creating a home, sandbox path rules
├── test_profiles.py          # child profiles: defaults, validation, writing
├── test_subjects.py          # subject packs, front matter, lesson parsing
├── test_codes.py             # one-time exit codes
├── test_sessionlog.py        # session log parser and its warnings
├── test_ledger.py            # weeks, mastery, S metric, briefing facts
├── test_report.py            # the parent's digest text
├── test_transcript.py        # readable transcripts saved to HIL_transcripts
├── test_sandbox.py           # rendering sandboxes, briefing, runtime archive
├── test_sandbox_runtime.py   # the verify-only entry point (in-process)
├── test_cli.py               # every command, in-process
├── test_end_to_end.py        # real subprocesses and the real .pyz
└── test_package_hygiene.py   # design-rule guards (imports, sizes, docs, SKILL format)
```

**Framework:** pytest (`pytest-cov` optional)
**Config:** `pyproject.toml` → `[tool.pytest.ini_options]`
`testpaths = ["tests"]`, `pythonpath = ["."]`, `addopts = "-q"`
**conftest.py:** `tests/conftest.py` exports the fixtures below. Run everything with `pytest`, coverage with
`pytest --cov=tutor --cov-report=term-missing`. Expected: all pass, ~99% (the uncovered lines are entry-point stubs run only in subprocesses).

---

## Fixture Patterns

All fixtures build inside `tmp_path`; nothing touches real folders.

```python
# A fresh tutor home (defaults.toml, folders), a child, the physics pack, a built sandbox
def test_example(home, adam, physics, sandbox, now):
    assert (sandbox / "SKILL.md").is_file()
```

```python
# Write session logs with a chosen start time and a file mtime `minutes` later
def test_logs(make_session, tmp_path):
    make_session(tmp_path, stamp="2026-10-06_0900", minutes=20,
                 lines=["1 | child | ADJACENT | - | - | why is the sky blue"],
                 summary=['ended_by = "code"', 'mastered = ["forces.0"]'])
```

```python
# Run the CLI in-process (test_cli.py defines this fixture; copy it for new CLI tests)
def test_cmd(run, home, adam):
    code, out, err = run("sandbox", "adam", home=home)
```

```python
# Real subprocess + real archive (test_end_to_end.py helpers)
home, sandbox, codes = make_home(tmp_path)          # init, child add, sandbox, codes new
assert pyz(sandbox, "verify", codes[0], cwd=tmp_path).stdout.strip() == "OK"
```

**Fixed values:** `now` is `2026-10-11 09:15` (a Sunday; its week starts `2026-10-05`). `summary_ok` is a valid summary block.
**Speed:** exit-code hashing uses scrypt (~60 ms per code), so keep batches to 1-3 codes in tests.
**Parametrization:** `test_profiles.py` and `test_subjects.py` parametrize invalid inputs as `(input, expected message fragment)`; `test_sessionlog.py` parametrizes bad log lines the same way.

---

## Test File Inventory

| File | What it covers |
|---|---|
| `test_paths.py` | Home creation and lookup (explicit, env, ancestor), sandbox folder names, `is_inside_a_sandbox` with `..` |
| `test_profiles.py` | Slugs, default merging, every field's validation, TOML escaping round trip, overwrite refusal |
| `test_subjects.py` | Built-in physics pack, home packs overriding built-ins, front matter, every malformed-pack error, picture lines resolved to files (missing, repeated, none) |
| `test_codes.py` | Code shape, hashes-only storage, one-time use, batch protection, corrupt stores, leak pattern |
| `test_sessionlog.py` | Transcript parsing, derived facts, summary validation, all warnings, file-name rules |
| `test_ledger.py` | Week boundaries, first-mastery dates, minutes by choice, S formula, briefing facts |
| `test_transcript.py` | Turn lines and tags, header/footer, unfinished sessions, warnings, file naming, rehearsal folder, replace-on-resave, deleting only one child's rehearsal transcripts |
| `test_report.py` | Digest content in each situation (no sessions, finished, unfinished, targets, warnings, complete) |
| `test_sandbox.py` | Rendered files, refresh without data loss, all-or-nothing builds, briefing text, notes safety, runtime archive contents, delete_sandbox safety (bad ids, locked folders), pictures copied and dropped on refresh, SKILL picture wording |
| `test_sandbox_runtime.py` | OK/NO/ERROR outputs and exit statuses, argument forms, "nothing but verify" |
| `test_cli.py` | Each command's output and errors, rehearsal isolation, home resolution, `delete` and `reset` (rehearsal vs real, `--confirm`, transcripts kept or removed, factory state) |
| `test_end_to_end.py` | Full setup-to-next-briefing cycle via subprocess, verify-only runtime, children isolated, a dry run from creation to deletion |
| `test_package_hygiene.py` | Runtime imports, no dependencies, docstrings, size limits, print rule, dead placeholders, SKILL example parses, every picture page is small, self-contained, well-formed and says how to close, every Draw it block fits 12 x 60, API.md lists every public function, the full cheatsheet lists every command (read from the real parser) and every `--flag`, both short sheets' commands parse, the docs describe the sandbox contents, session-admin sheet commands all parse |

---

## Conventions

- **File names:** `test_<module>.py`, matching `tutor/<module>.py`; cross-cutting tests use a descriptive name.
- **Class grouping:** none; flat functions.
- **Test naming:** `test_<subject>_<expected outcome>` written as a sentence, e.g. `test_wrong_code_consumes_nothing`.
- **Assertions:** plain `assert`; compare whole values where practical.
- **Expected exceptions:** `with pytest.raises(SomeTutorError, match="fragment of the message")`. Always match the message, because the message is the user interface.
- **No global state:** use `tmp_path`; use `monkeypatch` for module constants; never write outside `tmp_path`.
- **Every new failure path gets a test** that asserts nothing was changed before raising (look at `test_a_bad_template_changes_nothing`).
- **New CLI command:** add it to `test_cli.py`, to the cheatsheet, and to the end-to-end cycle if it touches files.
- **Placeholders:** `test_package_hygiene.py` fails on a template variable that nothing uses and on any unknown variable, so add both sides together.

---

## Common Imports

```python
import pytest

from tutor import cli, codes, sandbox
from tutor.errors import CodeError, ProfileError, SandboxError, SubjectError
from tutor.paths import create_home, find_home
from tutor.profiles import add_profile, load_profile
from tutor.sessionlog import load_sessions, parse_session
from tutor.subjects import load_subject
```

---

*Last updated: 2026-10-12 — Think about lines (test_subjects.py) and the reply-first turn-order rule (test_package_hygiene.py); earlier: dry-run auto-delete on `review --rehearsal` with `--save-session` (test_cli.py, test_end_to_end.py); earlier: added delete/reset, the dry-run sheet, prepared pictures and Draw it diagrams (pack format, sandbox copy, hygiene checks), transcript saving (test_transcript.py, review/--saveTranscript cases), docs-drift tests and the vector lesson check.*

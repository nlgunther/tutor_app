# API reference

The command line is the supported interface. These modules sit behind it; each is small and has its own tests. Dependencies run downward: `cli` uses everything, `codes` and `errors` use nothing.

## tutor.errors

Every expected failure derives from `TutorError`, which the CLI prints as `error: <message>` with exit status 1. Subclasses: `HomeError`, `ProfileError`, `SubjectError`, `CodeError`, `SandboxError`, `LogError`.

## tutor.paths

### Home
`Home(root: Path)`. Properties `marker_path`, `defaults_path`, `children_dir`, `subjects_dir`, `sandboxes_dir`, `transcripts_dir` (`HIL_transcripts`, created when the first transcript is saved).
- `sandbox_dir(child_id, rehearsal=False) -> Path`: `sandboxes/<id>` or `sandboxes/<id>-rehearsal`.
- `is_inside_a_sandbox(path) -> bool`: True for any path under `sandboxes/`, with `..` and links resolved. Used to keep the paper list of codes out of reach.

### find_home(explicit, env, cwd) -> Home
`--home`, then `$TUTOR_HOME`, then the nearest folder above `cwd` containing `tutor.toml`. Raises `HomeError`.

### write_text(path, text)
UTF-8 with LF endings on every platform, so files and their hashes match everywhere.

### create_home(root) -> Home
Creates folders, `defaults.toml` and `tutor.toml`. Raises `HomeError` if the home exists.

## tutor.profiles

### ChildProfile
Frozen dataclass: `child_id, name, description, age, pronouns, reading_level, bridges, subject, adjacent_per_session, adjacent_per_week, target_minutes_per_week, target_concepts_per_week`. `targets_set` is True when both targets are set.

### load_profile(home, child_id) -> ChildProfile
Merges `children/<id>.toml` over `defaults.toml`; rejects unknown, missing or out-of-range fields with `ProfileError`.

### add_profile(home, name, description, overrides=None) -> ChildProfile
Writes only what differs from the defaults. Refuses to overwrite.

### list_children(home) -> list[str]
### slugify(name) -> str
`slugify("Mary-Ann") == "maryann"`.

## tutor.subjects

### load_subject(home, subject_id) -> Subject
Your `subjects/<id>/` first, then the built-in pack. `Subject` has `lessons`, `lesson(id)`, `remaining(mastered) -> tuple[Lesson, ...]` (empty when complete), `pictures` (the prepared picture files the units name, each verified to exist, no repeats), plus `title, scope_in, adjacent_examples, bridge_map, greeting, roadmap, units`. A lesson may carry a `- **Think about:** text` line (under 240 characters, else `SubjectError`), exposed as `Lesson.think_about` (`None` when absent): a study-only prompt the tutor shows while it saves or loads. A lesson names a picture with a `- **Picture:** name` line; the pack must then hold `diagrams/name.html`, otherwise `SubjectError`.

### available_subjects(home) -> list[str]
### split_front_matter(text, label) -> (dict, str)
Splits `+++` TOML front matter from the Markdown body.

## tutor.codes

### new_codes(path, count, *, replace=False) -> list[str]
Creates `count` codes of 12 characters (no I, O, 0, 1) and stores only salted scrypt hashes. Refuses while unused codes remain unless `replace=True`. Returns the plaintext **once**.

### verify_and_consume(path, code) -> bool
True if the code matches an unspent one (which is then spent). Case, spaces and dashes are ignored. Wrong codes consume nothing.

### status(path) -> CodeStatus
`CodeStatus(issued, remaining)`.

### normalize(code) -> str
Upper-cases and strips spaces and dashes: `normalize("k7qf-3m9t xa2b") == "K7QF3M9TXA2B"`.

## tutor.sessionlog

### parse_session(path) -> SessionRecord
### load_sessions(folder) -> SessionLoad
`SessionLoad(records, unrecognised)`, oldest first. `SessionRecord` exposes `finished, minutes, initiated_by, mastered, adjacent_used, safety_turns, redirects, lessons_covered, warnings`. Minutes are the file's last-modified time minus the start time in its name.

### select_session(records, session_id=None) -> SessionRecord
The latest record, or the one named. Raises `LogError` when there are none or the id is unknown.

### session_id_for(child_id, now) -> str
`session_id_for("adam", datetime(2026, 10, 11, 9, 5)) == "2026-10-11_0905_adam"`.

## tutor.ledger

Pure functions over records: `week_start(day)`, `compute_progress(records, subject) -> Progress`, `week_totals(records, progress, start) -> WeekTotals`, `s_metric(m, c, m0, c0)`, `start_facts(records, subject, now) -> StartFacts`.

## tutor.report

### render_digest(profile, subject, load, now, session_id=None) -> str
The text `tutor review` prints.


## tutor.transcript

- `render_transcript(profile, subject, record) -> str`: the session as Markdown (header, every turn with its class and redirect tags, notes, warnings).
- `delete_rehearsal_transcripts(home, child_id) -> int`: removes that child's files from `HIL_transcripts/rehearsal/` and returns how many; real transcripts are never touched.
- `save_transcript(home, profile, subject, record, rehearsal) -> Path`: writes `HIL_transcripts/<session id>.md` (rehearsals in `HIL_transcripts/rehearsal/`). `tutor review` calls it when given `--saveTranscript` or when the session's summary has `save_transcript = true`.

## tutor.sandbox

- `render_sandbox(home, profile, subject, *, rehearsal, now) -> Path`: builds or refreshes a sandbox (SKILL.md, start_prompt.md, `units/`, `diagrams/` when the pack has pictures, `sessions/`, the runtime); renders everything before writing anything.
- `render_start_prompt(profile, subject, load, now, initiated_by) -> str`; `write_start_prompt(dest, profile, subject, now, initiated_by) -> SessionLoad`.
- `build_runtime(target)`: zips the verify-only runtime.
- `require_sandbox(home, child_id, rehearsal) -> Path`; `delete_sandbox(home, child_id, rehearsal)` deletes one sandbox folder and everything in it (refuses invalid child ids, so `..` or a path can never reach outside `sandboxes/`; a missing folder is left alone; a folder Windows has open raises `SandboxError` saying to close the chat and retry).
- `base_context(profile, subject)`, `render_text(text, context, label)`: the `${placeholder}` vocabulary for templates.

## tutor.sandbox_runtime

`main(argv, codes_path=None) -> int`. Shipped as `tutor_sandbox.pyz`. Only `verify` exists. Imports nothing but `tutor.codes` and `tutor.errors`, enforced by a test.

## tutor.cli

`main(argv=None, *, now=None, env=None, cwd=None) -> int` and `build_parser()`. Handlers are private and return the text to print. `tutor reset` and `tutor delete` act on a real sandbox only with `--confirm <child id>`; rehearsals need none.

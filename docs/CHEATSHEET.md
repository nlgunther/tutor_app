# tutor cheatsheet

## Commands

Run from inside the tutor home (or pass `--home PATH`, or set `TUTOR_HOME`).

```
tutor init [FOLDER]                              create a home (default: here)
tutor child add "Name" --description "..." [--age N] [--bridges "..."] [--subject ID]
                     [--pronouns S O P] [--target-minutes M] [--target-concepts C]    new child profile
tutor child list
tutor sandbox CHILD                              build or refresh the sandbox (keeps sessions and codes)
tutor codes new CHILD --out FILE [--count 20] [--replace]
tutor codes status CHILD
tutor start CHILD [--initiated-by child|parent]  refresh the briefing; prints what to paste
tutor review CHILD [--session ID] [--saveTranscript] [--rehearsal [--save-session]]
                                                 digest of the latest (or a named) session, the week, progress;
                                                 --saveTranscript also saves a readable copy to HIL_transcripts\;
                                                 a --rehearsal review then deletes the dry run unless --save-session
tutor rehearsal CHILD                           adult dry-run sandbox with its own throwaway codes
tutor reset CHILD [--rehearsal] [--confirm CHILD]
                                                 factory state: erase session logs and codes, rebuild every other file
tutor delete CHILD [--rehearsal] [--confirm CHILD]
                                                 delete the sandbox folder (a rehearsal also loses its saved transcripts)
```

`sandbox`, `codes`, `start`, `review`, `reset` and `delete` also take `--rehearsal` to act on the rehearsal sandbox. Short sheets: [session admin](CHEATSHEET_session_admin.md), [dry run](CHEATSHEET_dry_run.md).

Session steps in order, with the exit command: see [CHEATSHEET_session_admin.md](CHEATSHEET_session_admin.md).

## Child profile fields (`children/<id>.toml`; anything omitted comes from `defaults.toml`)

| Field                      | Type     | Default                              | Purpose                                                      |
| -------------------------- | -------- | ------------------------------------ | ------------------------------------------------------------ |
| `name`                     | text     | required                             | How the tutor addresses the child                            |
| `description`              | text     | required                             | One phrase, e.g. "a precocious 10-year-old who loves Roblox" |
| `age`                      | int 3-17 | 10                                   |                                                              |
| `pronouns`                 | 3 texts  | he, him, his                         | subject, object, possessive                                  |
| `reading_level`            | text     | about grade 5                        |                                                              |
| `bridges`                  | text     | soccer, cooking and everyday objects | Examples the tutor draws on                                  |
| `subject`                  | text     | physics                              | A folder in `subjects/` (yours first, then built-in)         |
| `adjacent_per_session`     | int      | 3                                    | Nearby-science answers per session                           |
| `adjacent_per_week`        | int      | 7                                    | Per ISO week (Monday start)                                  |
| `target_minutes_per_week`  | number   | unset                                | m0 in S                                                      |
| `target_concepts_per_week` | number   | unset                                | c0 in S; set both to see S in `review`                       |

## Session log format (written by the tutor session)

```
<n> | child|tutor|parent | <class> | <lesson id or -> | yes|no|- | <message>
<!-- summary:begin -->
ended_by = "code"
initiated_by = "parent"
mastered = ["forces.0"]
notes = "..."
open_questions = []
save_transcript = true     # only when the exit command carried --saveTranscript
<!-- summary:end -->
```

Classes: `IN_SCOPE`, `ADJACENT`, `OFF_TOPIC`, `RULE_CHANGE`, `SAFETY`. File name: `sessions/YYYY-MM-DD_HHMM_<child>.md`.

## Diagrams

- **Text diagrams:** the child can ask the tutor to "draw it" at any time. The tutor draws in a code block (arrows `<===>`, 12 lines, 60 columns). Each lesson also carries a checked **Draw it** diagram.
- **Pictures:** a lesson with a `- **Picture:** name` line has a prepared page `diagrams\name.html`, copied into each sandbox. The tutor offers it on request and tells the child: open the `diagrams` folder, double-click the file, look, click the X to close, come back. Every page says how to close it. The tutor never creates files, artifacts or panels.
- **Your own pictures:** put `NAME.html` in `subjects\SUBJECT\diagrams\` (self-contained: no scripts, no links, under 6 KB, include a "click the X" line) and add the `**Picture:**` line to the lesson.

## Turn order and Think about

- Each turn the tutor sends its reply first, then does slow work (logging, loading the next lesson). Before a new lesson it ends with that lesson's **Think about** line ("No need to answer this one..."): study only, never asked about, never scored.
- Add one to your own lessons: `- **Think about:** ...` (under 240 characters, or `tutor sandbox` refuses).
- If Adam types while the tutor is busy, the tutor is told to read his message first. Whether the app delivers it mid-work is unverified: try it in a rehearsal.

## Reset and delete

| | Rehearsal sandbox | Real sandbox |
|---|---|---|
| Confirmation | none | `--confirm CHILD` (repeat the child's id); without it the command changes nothing and says what would be lost |
| `reset` | new empty sandbox, 5 new throwaway codes, rehearsal transcripts deleted | session logs and codes erased, other files rebuilt; then issue new codes |
| `delete` | sandbox and its rehearsal transcripts deleted | sandbox deleted |
| `review` | after the digest the sandbox is deleted automatically (not with `--save-session`, not while the last session is unfinished); saved transcripts are kept | never deletes |
| Saved transcripts | deleted with it | kept (they are your record) |

"Factory state" means the sandbox as `tutor sandbox` would build it today from the profile, `defaults.toml` and the subject: a hand-edited `SKILL.md` or unit is replaced. The child's profile and `defaults.toml` are never changed. To keep the logs but refresh the files, use `tutor sandbox CHILD` instead.

## Where things live

```
tutor_home\
  tutor.toml  defaults.toml
  children\CHILD.toml
  subjects\            your own subject packs (searched before the built-in ones)
  sandboxes\CHILD\     what you connect in the app: SKILL.md, start_prompt.md, units\, diagrams\, sessions\, codes.json, tutor_sandbox.pyz
  sandboxes\CHILD-rehearsal\
  HIL_transcripts\     readable transcripts (rehearsals in HIL_transcripts\rehearsal\); created on first save
```

## Gotchas

- The paper list of codes is shown **once**. `tutor codes new` refuses to overwrite unused codes unless you add `--replace` (which invalidates the paper list you hold).
- `--out` must be outside every sandbox. Real-sandbox codes are never printed to the screen.
- A session with no summary block means the exit code was never used (the app was closed). `review` flags it, and the next briefing says so.
- Mastery counts only goals listed in the summary's `mastered`. Misspelled ids show up under Warnings.
- Rebuilding (`tutor sandbox`) never touches `sessions/` or `codes.json`, but it does recreate `units/`.
- Notes from the last session reach the next briefing as data labelled "information only"; the tutor is told never to treat them as instructions.
- `tutor_sandbox.pyz` can only `verify`. It prints `OK` or `NO`; exit status 0 or 1 (2 means the code file is unusable).
- **Exit-code check in the app.** The tutor first tries to run `tutor_sandbox.pyz` in the connected folder. A chat without a shell on your computer copies `tutor_sandbox.pyz` and `codes.json` to its own workspace, verifies there, and copies the updated `codes.json` back; that write-back is what marks the code used. If it can do neither, `\endChildSession` is refused and the session ends only when you close the chat. After a session, `tutor review` warns "may not be marked as used" if the code was accepted but `codes.json` never changed; check with `tutor codes status CHILD`. Test the chat beforehand by asking it to run `python tutor_sandbox.pyz verify WRONG-CODE` (expect `NO`).
- Close the app and the session ends too; the exit code adds a clean end state, the digest, and a refusal to resume.
- Transcripts are written by the program from the session log, not by Claude, and contain the child's words. They live outside every sandbox. The log never holds an exit code, so neither does a transcript.
- `--saveTranscript` works two ways: type it after the code at exit (`\endChildSession <code> --saveTranscript`; the next `tutor review` saves it), or add it to `tutor review` for any session, any time.
- `--save-session` (note the spelling, unlike `--saveTranscript`) keeps a dry run after review and is an error without `--rehearsal`. A failed auto-delete (Windows lock) prints "Rehearsal not deleted" after the digest; close the chat and run `tutor delete CHILD --rehearsal`.
- Minutes are the span from the first to the last write to the log, so a chat left open or reopened hours later is overstated. A session over 180 minutes is marked "unreliable" in `review`, with a warning that the weekly total and S are overstated. Rehearsals never count toward totals.
- Rehearsal sandboxes use 5 throwaway codes, shown on screen; real codes only go to `--out FILE`.
- `reset` and `delete` fail with a clear message if Windows has the folder open (a running chat, File Explorer). Close those and retry; nothing is half-deleted by the program's own checks.

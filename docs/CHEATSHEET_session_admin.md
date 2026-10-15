# Session admin cheatsheet

`CHILD` is `adam` or `david`. Run from `tutor_home` (or add `--home PATH`). If `tutor` isn't found, use `python -m tutor`.

## Run a session

| # | Do this | Notes |
|---|---|---|
| 1 | `tutor sandbox CHILD` | Build or refresh. Safe to repeat; keeps logs and codes. |
| 2 | `tutor codes new CHILD --out ..\CHILD_codes.txt` | Only when `tutor codes status CHILD` shows none left. Prints 20 codes once. Print the file, then keep it away from the child and the session. |
| 3 | `tutor start CHILD` | Add `--initiated-by child` if the child asked to study. Prints the two lines to paste. |
| 4 | New chat in the Claude desktop app, connect **only** `sandboxes\CHILD` | |
| 5 | Paste the two lines from step 3 | Claude replies "Ready. Waiting for CHILD.  CHILD - please type 'let's start' to begin." |
| 6 | Child types `let's start` | |
| 7 | **You** type `\endChildSession <code>` | Add `--saveTranscript` to keep a readable copy. Spaces and dashes in the code are fine. Cross the code off. |
| 8 | `tutor review CHILD` | Digest, week, progress, warnings. With `--saveTranscript` in step 7, it also saves the transcript. |

Exit command examples:
```
\endChildSession K7QF-3M9T-XA2B
\endChildSession K7QF-3M9T-XA2B --saveTranscript
```
A wrong code is refused and the session continues. Closing the app ends the session without a summary; `review` flags it.

## Dry run (adults)

See [CHEATSHEET_dry_run.md](CHEATSHEET_dry_run.md): `tutor rehearsal CHILD`; `tutor review CHILD --rehearsal` ends it (auto-deletes; `--save-session` keeps it). Then `tutor reset CHILD --rehearsal` to repeat or `tutor delete CHILD --rehearsal` to remove. Never touches the real sandbox.

## Diagrams

The child can say "draw it" for a text diagram any time. For a bigger picture the tutor says: open the `diagrams` folder, double-click the file, then click the **X** to close it and come back. If a panel opens on the right by itself, click its **X**. After updating the program, run `tutor sandbox CHILD` so the sandbox gets the pictures.

## Transcripts

`tutor review CHILD --saveTranscript` writes `HIL_transcripts\<session id>.md` (rehearsals: `HIL_transcripts\rehearsal\`). `--session ID` picks an older session.

## Quick fixes

| Problem | Fix |
|---|---|
| Lost the paper list | `tutor codes new CHILD --out ..\codes2.txt --replace` |
| Out of codes | `tutor codes new CHILD --out FILE` |
| `review` says a code "may not be marked as used" | Run `tutor codes status CHILD`; if the unused count did not drop, the code is still valid: replace it with `tutor codes new CHILD --out FILE --replace` when convenient |
| `review` says a turn looks like an exit code | Delete that line from the log; `--replace` the codes |
| Edited a profile, defaults or unit | `tutor sandbox CHILD` |
| Start a real sandbox over (erases logs and codes) | `tutor reset CHILD --confirm CHILD`, then new codes |
| Remove a real sandbox | `tutor delete CHILD --confirm CHILD` (saved transcripts are kept) |

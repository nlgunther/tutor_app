# tutor

`tutor` builds a locked-down tutoring sandbox for each of your children, runs the paperwork around it (exit codes, session briefings, weekly progress), and gives you a digest of every session.

The tutoring itself is done by Claude in the desktop app, supervised by you. This program prepares the folder Claude works in, keeps the secrets out of its reach, and reads back what happened.

## The problem it solves

A child's chat with an AI should stay on one subject, be recorded, end only when a parent says so, and leave the parent with something readable. Doing that by hand means retyping the date, the weekly question count and last session's notes into a prompt, hand-copying logs, and trusting the chat to enforce its own exit. `tutor` automates the parent's side and makes the exit a one-time code that the session can check but never see.

## Quick start

Requires Python 3.11 or newer. No other packages.

```
cd tutor_app
pip install -e .                       # adds the `tutor` command (or use `python -m tutor` from this folder)
cd ..\tutor_home                       # a home with Adam and David already set up
tutor sandbox adam                     # build Adam's sandbox
tutor codes new adam --out ..\adam_codes.txt     # 20 one-time exit codes -> print this file, then keep it away from Adam
tutor start adam                       # prints the two lines to paste into a new Claude chat
```

Connect the folder it prints (`sandboxes\adam`) in the Claude desktop app, paste the two lines, and when Adam types **let's start** the session begins. When you are done, type `\endChildSession <one of your codes>`. Afterwards:

```
tutor review adam                      # digest: what was covered, mastered, asked, redirected
```

## Key features

- **One sandbox per child.** Only that folder is connected to a session, so a child's session cannot see another child's logs or codes.
- **One-time exit codes.** Stored only as salted hashes. The session checks a code through `tutor_sandbox.pyz`, a verify-only program that cannot create or reset codes.
- **Briefings written for you.** `tutor start` fills in the date, this week's adjacent-question count, last session's notes and the next lesson.
- **Progress tracking.** Each lesson has a goal; the tutor records which goals were met; `tutor review` shows mastery, weekly minutes, minutes the child chose, and the S score once you set targets.
- **Readable transcripts.** `tutor review adam --saveTranscript` (or `--saveTranscript` on the exit command) saves a transcript to `HIL_transcripts\`, outside every sandbox.
- **Diagrams.** The tutor draws text diagrams on request; each lesson carries a checked one, and prepared pictures open with a double-click and close with the X.
- **Rehearsals.** `tutor rehearsal adam` makes a throwaway copy for adult dry runs that never counts toward Adam's totals and is deleted when you review it (`--save-session` keeps it); `tutor reset` and `tutor delete` return a sandbox to factory state or remove it (a real one only after `--confirm`).
- **Extensible by files.** A new child is a TOML file; a new unit or subject is a Markdown file plus a TOML file. No code changes.

## Where to go next

- [CHEATSHEET_dry_run.md](CHEATSHEET_dry_run.md): a dry run from creation to deletion
- [CHEATSHEET_session_admin.md](CHEATSHEET_session_admin.md): the short sheet for running a session, start to exit
- [CHEATSHEET.md](CHEATSHEET.md): every command and setting on one page
- [workflows.md](workflows.md): setup, a normal session, dry runs, adding children and subjects, recovering from mishaps
- [API.md](API.md): modules and functions
- [../TEST_GUIDE.md](../TEST_GUIDE.md): how the tests are organised

## What it does not do

It cannot make the Claude session obey. The sandbox's SKILL.md instructs Claude; your supervision is the real control. The program reduces what a tricked session can reach (it cannot read codes or other children's folders, and cannot mint codes), and it makes drift visible in the digest.

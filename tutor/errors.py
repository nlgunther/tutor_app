"""One exception family: every expected, user-fixable failure is a TutorError.

The CLI prints a TutorError as a one-line message; anything else is a bug and shows a traceback.
Ships inside tutor_sandbox.pyz, so it must stay import-free.
"""


class TutorError(Exception):
    """Base class for expected failures (bad profile, missing file, wrong command)."""


class HomeError(TutorError):
    """The tutor home folder is missing, already exists, or cannot be located."""


class ProfileError(TutorError):
    """A child profile is missing, malformed or has unknown or invalid fields."""


class SubjectError(TutorError):
    """A subject pack or unit file is missing or malformed."""


class CodeError(TutorError):
    """The exit-code store is missing, corrupt, or the request would invalidate unused codes."""


class SandboxError(TutorError):
    """A sandbox cannot be built, found, or safely modified."""


class LogError(TutorError):
    """A session log cannot be found or read."""

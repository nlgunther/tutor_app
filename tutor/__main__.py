"""Allows `python -m tutor ...` without installing the package."""
import sys

from tutor.cli import main

sys.exit(main())

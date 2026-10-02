"""SpaceFruit Django backend launcher.

The browser UI is now React and the HTTP API is served by Django.
Run this file to start the backend on http://127.0.0.1:8000.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spacefruit_api.settings")

if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    execute_from_command_line([sys.argv[0], "runserver", "127.0.0.1:8000", *sys.argv[1:]])

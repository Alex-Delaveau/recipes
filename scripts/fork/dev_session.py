"""Print a valid Django `sessionid` for the dev user (default: demo), for headless UI checks.

Only for local/cloud development databases. Never run against production data.
Usage: .venv/bin/python scripts/fork/dev_session.py [username]
"""
import os
import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "recipes.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY, get_user_model  # noqa: E402

username = sys.argv[1] if len(sys.argv) > 1 else "demo"
user = get_user_model().objects.get(username=username)
session = import_module(settings.SESSION_ENGINE).SessionStore()
session[SESSION_KEY] = str(user.pk)
session[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
session[HASH_SESSION_KEY] = user.get_session_auth_hash()
session.create()
print(session.session_key)

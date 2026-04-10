"""
PythonAnywhere WSGI entry point.

In the PythonAnywhere web tab, set:
  Source code:    /home/<username>/newflasknba
  Working dir:    /home/<username>/newflasknba
  WSGI file:      /home/<username>/newflasknba/wsgi.py
  Virtualenv:     /home/<username>/newflasknba/venv

Environment variables to set in the PA web tab:
  DATABASE_URL=sqlite:////home/<username>/newflasknba/instance/nba.sqlite
  SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
  CURRENT_SEASON=2026
  RESEND_API_KEY=<your key>
  MAIL_FROM=nba@yourdomain.com
"""

import sys
import os

# Add src/ to path so `nba_predictions` is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from nba_predictions import create_app  # noqa: E402

application = create_app("production")

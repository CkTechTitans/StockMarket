"""
wsgi.py
=======
Entry point for gunicorn on Render.
Gunicorn calls this file: gunicorn wsgi:app
"""
import sys
import os

# Make sure backend is importable
ROOT    = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND)

from app import app

if __name__ == "__main__":
    app.run()
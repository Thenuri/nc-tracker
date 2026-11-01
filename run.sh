#!/bin/bash
# Start the NC Tracker on http://127.0.0.1:8000/ (Ctrl+C to stop).
# cd to this script's folder first so it works from anywhere.
cd "$(dirname "$0")"
.venv/bin/python manage.py runserver

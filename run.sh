#!/usr/bin/env bash
# macOS / Linux: chạy web tại http://127.0.0.1:8000
cd "$(dirname "$0")"
source .venv/bin/activate
uvicorn app.main:app --reload

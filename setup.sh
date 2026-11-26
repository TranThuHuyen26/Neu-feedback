#!/usr/bin/env bash
# macOS / Linux: cài đặt lần đầu
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Đã tạo file .env. Hãy sửa dòng DATABASE_URL cho đúng mật khẩu PostgreSQL, tạo cơ sở dữ liệu neu_feedback, rồi chạy lại ./setup.sh"
  exit 0
fi
alembic upgrade head
python -m scripts.seed --reset
echo "Xong! Chạy: ./run.sh"

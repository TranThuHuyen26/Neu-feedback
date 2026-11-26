@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === NEU Feedback: cai dat lan dau ===
python --version >nul 2>&1 || (echo [LOI] Chua cai Python. Tai tai https://www.python.org/downloads/ va tick "Add python.exe to PATH". & pause & exit /b)
if not exist .venv (echo Dang tao moi truong ao... & python -m venv .venv)
call .venv\Scripts\activate.bat
echo Dang cai thu vien (lan dau mat vai phut)...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt || (echo [LOI] Cai thu vien that bai. Kiem tra ket noi mang. & pause & exit /b)
if not exist .env (
  copy .env.example .env >nul
  echo.
  echo [BUOC TIEP THEO] Da tao file .env. Hay mo file .env, sua dong DATABASE_URL cho dung mat khau PostgreSQL,
  echo va tao co so du lieu neu_feedback trong pgAdmin. Sau do bam dup lai file nay.
  pause
  exit /b
)
echo Dang tao co so du lieu...
alembic upgrade head
python -m scripts.seed --reset
echo.
echo === XONG! Bay gio mo file 2-chay-web.bat ===
pause

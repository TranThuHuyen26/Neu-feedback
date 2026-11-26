@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv (echo Ban chua cai dat. Hay chay file 1-cai-dat-lan-dau.bat truoc. & pause & exit /b)
call .venv\Scripts\activate.bat
echo Dang khoi dong... Trinh duyet se tu mo sau vai giay.
echo Nhan Ctrl + C trong cua so nay de tat web.
start "" cmd /c "timeout /t 4 >nul & start http://127.0.0.1:8000"
uvicorn app.main:app --reload
pause

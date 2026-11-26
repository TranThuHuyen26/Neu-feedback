@echo off
chcp 65001 >nul
cd /d "%~dp0"
call .venv\Scripts\activate.bat
echo Tao lai du lieu mau (xoa du lieu hien tai)...
python -m scripts.seed --reset
pause

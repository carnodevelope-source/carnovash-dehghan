@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv" (
    py -3.10 -m venv .venv
    if errorlevel 1 py -3.11 -m venv .venv
    if errorlevel 1 py -3.12 -m venv .venv
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt

echo.
echo Install finished.
echo Run environment check with:
echo   .venv\Scripts\python check_runtime.py
endlocal

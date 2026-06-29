@echo off
setlocal
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

set INPUT_VIDEO=%~1
if "%INPUT_VIDEO%"=="" set INPUT_VIDEO=vid1.mp4

python video_plate.py --input-video "%INPUT_VIDEO%" --output-video "io/output/single_result.mp4"
endlocal

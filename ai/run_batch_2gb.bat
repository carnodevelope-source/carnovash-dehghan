@echo off
setlocal
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

python batch_video_plate.py ^
  --input-list "video_jobs_10.txt" ^
  --launch-interval 1 ^
  --max-concurrent 1 ^
  --success-count 3 ^
  --report-md "io/output/batch_report_2gb.md"

endlocal

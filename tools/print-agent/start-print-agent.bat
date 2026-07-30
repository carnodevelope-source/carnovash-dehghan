@echo off
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js نصب نیست. ابتدا Node.js را نصب کنید.
  pause
  exit /b 1
)
if not exist "node_modules\" (
  echo در حال نصب وابستگی‌های پرینت‌ایجنت...
  call npm install
  if errorlevel 1 (
    echo نصب وابستگی‌ها ناموفق بود.
    pause
    exit /b 1
  )
)
echo CarnoWash Print Agent در حال اجراست...
echo این پنجره را باز بگذارید تا چاپ مستقیم کار کند.
node server.mjs
pause

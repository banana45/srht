@echo off
setlocal
cd /d "%~dp0"

set PORT=6001
set OPEN_BROWSER=1
set APP_URL=http://127.0.0.1:6001

if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto error
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto error

python -m pip install -r requirements.txt
if errorlevel 1 goto error

echo.
echo Contract generator is starting. The browser will open automatically:
echo %APP_URL%
echo Keep this window open while using the tool.
echo.
python app.py
goto end

:error
echo.
echo Startup failed. Please check the messages above.
pause

:end

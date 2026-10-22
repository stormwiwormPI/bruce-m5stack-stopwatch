@echo off
setlocal
cd /d "%~dp0"

set "PY="
where py >nul 2>nul
if %errorlevel%==0 set "PY=py -3"
if not defined PY (
    where python >nul 2>nul
    if %errorlevel%==0 set "PY=python"
)

if not defined PY (
    echo.
    echo   [XX] Python 3 was not found.
    echo        Install it from https://www.python.org/downloads/
    echo        and make sure "Add Python to PATH" is checked.
    echo.
    pause
    exit /b 1
)

%PY% "%~dp0flash.py" %*
set "RC=%errorlevel%"

rem Keep the window open when the script was started by double-click.
if "%~1"=="" pause
exit /b %RC%

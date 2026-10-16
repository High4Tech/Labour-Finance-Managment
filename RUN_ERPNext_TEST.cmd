@echo off
setlocal
cd /d "%~dp0"
echo PLUS POINT - official ERPNext framework smoke-test on Windows Docker Desktop
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\test-erpnext-windows.ps1" -StopAfterTest
set "TEST_EXIT=%ERRORLEVEL%"
echo.
if "%TEST_EXIT%"=="0" (
    echo Framework smoke test: PASS
) else (
    echo Framework smoke test: FAILED - see diagnostic output above
)
echo.
echo Press a key to close this window.
pause >nul
exit /b %TEST_EXIT%

@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" goto missing
if not exist "app.py" goto missing
echo GGF Zonos2 - phone access is configured in the app's Settings tab.
"%~dp0.venv\Scripts\python.exe" "%~dp0app.py" %*
exit /b %ERRORLEVEL%
:missing
echo Run install.bat first.
exit /b 1

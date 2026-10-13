@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if not defined ZONOS2_PORT set "ZONOS2_PORT=1920"
echo ZONOS2 temporary phone access
echo Your PC runs generation; your phone opens the HTTPS address below.
echo PUBLIC PREVIEW: anyone with the link can use this app. No login is enabled.
echo Close this tunnel window or press Ctrl+C to end phone access.
echo The local model server stays open; close its own window to release model memory.
if not exist "tools" mkdir "tools"
if exist "tools\cloudflared.exe" goto verify
echo Downloading the pinned Cloudflare tunnel helper...
curl.exe --fail --location --retry 3 --continue-at - --output "tools\cloudflared.exe.partial" "https://github.com/cloudflare/cloudflared/releases/download/2026.7.1/cloudflared-windows-amd64.exe"
if errorlevel 1 goto failed
certutil.exe -hashfile "tools\cloudflared.exe.partial" SHA256 2>nul | findstr /i /c:"ccb0756de288d3c2c076d19764ca53e0849a10f2dd9c23f8656ac42bdeb45001" >nul
if errorlevel 1 goto failed
ren "tools\cloudflared.exe.partial" "cloudflared.exe"
if errorlevel 1 goto failed
:verify
certutil.exe -hashfile "tools\cloudflared.exe" SHA256 2>nul | findstr /i /c:"ccb0756de288d3c2c076d19764ca53e0849a10f2dd9c23f8656ac42bdeb45001" >nul
if errorlevel 1 goto failed
curl.exe --fail --silent --max-time 3 "http://127.0.0.1:%ZONOS2_PORT%/tts/capabilities" | findstr /c:"speaker_audio_upload" >nul
if not errorlevel 1 goto tunnel
echo Starting the native model server in its own window...
start "ZONOS2 native model server" /min "%ComSpec%" /c ""%~dp0run.bat" --batch 2 --dac-threads 1"
set "ZONOS2_WAIT=0"
:wait
curl.exe --fail --silent --max-time 3 "http://127.0.0.1:%ZONOS2_PORT%/tts/capabilities" | findstr /c:"speaker_audio_upload" >nul
if not errorlevel 1 goto tunnel
set /a ZONOS2_WAIT+=1 >nul
if %ZONOS2_WAIT% GEQ 120 goto notready
timeout.exe /t 1 /nobreak >nul 2>nul
goto wait
:tunnel
echo Local server is ready. Creating temporary HTTPS phone URL...
"%~dp0tools\cloudflared.exe" tunnel --config "%~dp0tools\phone-tunnel.yml" --no-autoupdate --protocol http2 --url "http://127.0.0.1:%ZONOS2_PORT%"
exit /b %ERRORLEVEL%
:notready
echo Model server did not become ready. Check its console for errors.
echo If another app uses port %ZONOS2_PORT%, set ZONOS2_PORT to a free port and retry.
exit /b 1
:failed
echo Tunnel helper download or hash verification failed. Files were preserved.
exit /b 1

@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0zonos2"
if not exist "zonos2-server.exe" goto missing
if not exist "models\zonos2-q6_k.gguf" goto missing
if not exist "models\dac.gguf" goto missing
if not exist "models\spk-encoder.gguf" goto missing
if not defined ZONOS2_PORT set "ZONOS2_PORT=1920"
set "ZONOS2_EXE=zonos2-server.exe"
set "ZONOS2_DEVICE=--cpu"
if /i "%ZONOS2_BACKEND%"=="cpu" goto ready
if not exist "cuda\zonos2-server.exe" goto ready
set "ZONOS2_EXE=cuda\zonos2-server.exe"
set "ZONOS2_DEVICE=--gpu"
:ready
echo Native ZONOS2 - local browser address http://127.0.0.1:%ZONOS2_PORT%/
echo Runtime: %ZONOS2_EXE% %ZONOS2_DEVICE%
echo Wait for the server-ready message before opening the browser.
"%ZONOS2_EXE%" "models\zonos2-q6_k.gguf" --dac "models\dac.gguf" --spk "models\spk-encoder.gguf" %ZONOS2_DEVICE% --host 127.0.0.1 --port %ZONOS2_PORT% --tts-default-voices-dir "default_voices" %*
exit /b %ERRORLEVEL%
:missing
echo Run install.bat first.
exit /b 1

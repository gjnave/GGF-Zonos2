@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
echo ZONOS2 native Windows evaluation - official v0.5.2 Vulkan runtime.
echo run.bat uses CPU mode unless the separately validated local CUDA runtime is present.
echo No WSL, Python, PyTorch, or administrator launch is needed.
echo Downloads official runtime and Q6_K, vocoder and speaker models into this folder.
if not exist "downloads" mkdir "downloads"
if not exist "zonos2" mkdir "zonos2"
if not exist "zonos2\models" mkdir "zonos2\models"
if not exist "zonos2\default_voices" mkdir "zonos2\default_voices"
if not exist "outputs" mkdir "outputs"
call :fetch "downloads\zonos2-windows-x64-vulkan-v0.5.2.zip" "https://github.com/Zyphra/zonos2.cpp/releases/download/v0.5.2/zonos2-windows-x64-vulkan.zip" "e89fb7396e3960ae0961f5a737ed0f988e16d3dece79618d35920cc916cc943c"
if errorlevel 1 goto failed
if exist "zonos2\zonos2-server.exe" goto models
tar.exe -xf "downloads\zonos2-windows-x64-vulkan-v0.5.2.zip" -C "%~dp0zonos2"
if errorlevel 1 goto failed
if not exist "zonos2\zonos2-server.exe" goto failed
:models
call :fetch "zonos2\models\zonos2-q6_k.gguf" "https://huggingface.co/Zyphra/ZONOS2-GGUF/resolve/75c877ec8ac86dda42bfc0e9968c87f29e10ef57/zonos2-q6_k.gguf?download=true" "349175207ce6521d4e89e2317f7862c68d15b8ee5ad876c1c3ce2938dc5c7e86"
if errorlevel 1 goto failed
call :fetch "zonos2\models\dac.gguf" "https://huggingface.co/Zyphra/ZONOS2-GGUF/resolve/75c877ec8ac86dda42bfc0e9968c87f29e10ef57/dac.gguf?download=true" "b5330fc112cfac5e7bae511a5083915ce5028899de4d7a4193dcc5874063532c"
if errorlevel 1 goto failed
call :fetch "zonos2\models\spk-encoder.gguf" "https://huggingface.co/Zyphra/ZONOS2-GGUF/resolve/75c877ec8ac86dda42bfc0e9968c87f29e10ef57/spk-encoder.gguf?download=true" "284849980047a811e2c2a13ce7527c8a6a286021df152e5325533d783240eb6d"
if errorlevel 1 goto failed
echo Setup complete. Run run.bat for the native Windows browser UI.
where ffmpeg.exe >nul 2>nul
if errorlevel 1 echo NOTE: Install ffmpeg or set ZONOS2_FFMPEG for voice-reference decoding. Plain text-to-speech does not need it.
exit /b 0
:fetch
if exist "%~1" (
  echo Verifying existing %~1 ...
  certutil.exe -hashfile "%~1" SHA256 2>nul | findstr /i /c:"%~3" >nul
  if errorlevel 1 exit /b 1
  exit /b 0
)
echo Downloading %~1 ...
curl.exe --fail --location --retry 3 --retry-delay 2 --continue-at - --silent --show-error --output "%~1.partial" "%~2"
if errorlevel 1 exit /b 1
echo Verifying downloaded %~1 ...
certutil.exe -hashfile "%~1.partial" SHA256 2>nul | findstr /i /c:"%~3" >nul
if errorlevel 1 (
  echo Hash mismatch. Partial file was preserved; no previous files were deleted.
  exit /b 1
)
for %%F in ("%~1") do ren "%~1.partial" "%%~nxF"
exit /b %ERRORLEVEL%
:failed
echo Setup stopped. Existing files and partial downloads have been preserved.
exit /b 1

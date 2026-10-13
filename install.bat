@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
echo ZONOS2 Windows setup - app-local uv and Python 3.11.
echo run.bat uses the included NVIDIA CUDA engine; CPU mode is optional.
echo No system Python is required. No CUDA toolkit or NVIDIA driver is installed by this setup.
echo Downloads Q6_K, vocoder and speaker models into this folder.
call :SETUP_ENVIRONMENT
if errorlevel 1 goto failed
if /i "%~1"=="/dependencies-only" exit /b 0
if not exist "downloads" mkdir "downloads"
if not exist "zonos2" mkdir "zonos2"
if not exist "zonos2\models" mkdir "zonos2\models"
if not exist "zonos2\default_voices" mkdir "zonos2\default_voices"
if not exist "outputs" mkdir "outputs"
if not exist "zonos2\zonos2-server.exe" goto failed
if not exist "zonos2\cuda\zonos2-server.exe" goto failed
if not exist "zonos2\web\tts_ui.html" goto failed
if not exist "app.py" goto failed
:models
call :fetch "zonos2\models\zonos2-q6_k.gguf" "https://huggingface.co/Zyphra/ZONOS2-GGUF/resolve/75c877ec8ac86dda42bfc0e9968c87f29e10ef57/zonos2-q6_k.gguf?download=true" "349175207ce6521d4e89e2317f7862c68d15b8ee5ad876c1c3ce2938dc5c7e86"
if errorlevel 1 goto failed
call :fetch "zonos2\models\dac.gguf" "https://huggingface.co/Zyphra/ZONOS2-GGUF/resolve/75c877ec8ac86dda42bfc0e9968c87f29e10ef57/dac.gguf?download=true" "b5330fc112cfac5e7bae511a5083915ce5028899de4d7a4193dcc5874063532c"
if errorlevel 1 goto failed
call :fetch "zonos2\models\spk-encoder.gguf" "https://huggingface.co/Zyphra/ZONOS2-GGUF/resolve/75c877ec8ac86dda42bfc0e9968c87f29e10ef57/spk-encoder.gguf?download=true" "284849980047a811e2c2a13ce7527c8a6a286021df152e5325533d783240eb6d"
if errorlevel 1 goto failed
echo Setup complete. Run run.bat. Phone access is built into the Settings tab.
echo Reference-audio decoding is provided by the app-local Python dependencies.
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

:SETUP_ENVIRONMENT
set "CACHE=%~dp0installer-cache"
set "UV=%CACHE%\uv\uv.exe"
set "UV_PYTHON_INSTALL_DIR=%CACHE%\python"
set "UV_PYTHON_DOWNLOADS=automatic"
set "VIRTUAL_ENV="
if not defined ZONOS_ENV_TARGET set "ZONOS_ENV_TARGET=%~dp0.venv"
if not exist "%CACHE%\uv" mkdir "%CACHE%\uv"
if not exist "%CACHE%\uv" goto environment_failed
if exist "%CACHE%\uv-0.12.24.zip" goto verify
echo Downloading pinned uv setup helper...
curl.exe --fail --location --retry 3 --continue-at - --output "%CACHE%\uv-0.12.24.zip.partial" "https://github.com/astral-sh/uv/releases/download/0.12.24/uv-x86_64-pc-windows-msvc.zip"
if errorlevel 1 goto environment_failed
certutil.exe -hashfile "%CACHE%\uv-0.12.24.zip.partial" SHA256 2>nul | findstr /i /c:"7c38608c8a18ee137d748a1773053b07ec8f3a30fab49aebaa6f4e4efeceb019" >nul
if errorlevel 1 goto environment_failed
ren "%CACHE%\uv-0.12.24.zip.partial" "uv-0.12.24.zip"
if errorlevel 1 goto environment_failed
:verify
certutil.exe -hashfile "%CACHE%\uv-0.12.24.zip" SHA256 2>nul | findstr /i /c:"7c38608c8a18ee137d748a1773053b07ec8f3a30fab49aebaa6f4e4efeceb019" >nul
if errorlevel 1 goto environment_failed
tar.exe -xf "%CACHE%\uv-0.12.24.zip" -C "%CACHE%\uv"
if errorlevel 1 goto environment_failed
if not exist "%UV%" goto environment_failed
if exist "%ZONOS_ENV_TARGET%\Scripts\python.exe" goto environment
if exist "%ZONOS_ENV_TARGET%" (
  echo Existing environment is incomplete. Use a new folder; it has not been deleted.
  goto environment_failed
)
echo Creating app-local managed Python 3.11. System Python is not used.
"%UV%" venv --managed-python --python 3.11 "%ZONOS_ENV_TARGET%"
if errorlevel 1 goto environment_failed
:environment
"%ZONOS_ENV_TARGET%\Scripts\python.exe" -c "import sys;assert sys.version_info[:2]==(3,11) and sys.maxsize>2**32"
if errorlevel 1 goto environment_failed
echo Installing application dependencies, including CUDA runtime libraries.
echo This does NOT install the CUDA toolkit, compiler, or NVIDIA driver.
"%UV%" pip install --python "%ZONOS_ENV_TARGET%\Scripts\python.exe" -r "%~dp0requirements.txt"
if errorlevel 1 goto environment_failed
"%UV%" pip check --python "%ZONOS_ENV_TARGET%\Scripts\python.exe"
if errorlevel 1 goto environment_failed
"%ZONOS_ENV_TARGET%\Scripts\python.exe" -c "import gradio, numpy, pandas, psutil, requests, imageio_ffmpeg"
if errorlevel 1 goto environment_failed
"%ZONOS_ENV_TARGET%\Scripts\python.exe" -c "import app; app.theme().to_dict(); app.build_demo()"
if errorlevel 1 goto environment_failed
"%ZONOS_ENV_TARGET%\Scripts\python.exe" "%~dp0launch-native.py" --check-environment
exit /b %ERRORLEVEL%
:environment_failed
echo Environment setup stopped. Existing files and partial downloads were preserved.
exit /b 1

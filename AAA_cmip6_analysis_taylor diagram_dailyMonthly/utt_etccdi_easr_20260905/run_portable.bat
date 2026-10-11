@echo off
setlocal
if "%~1"=="" (
  echo Usage: run_portable.bat CONFIG_JSON INPUT_DIRECTORY [OUTPUT_DIRECTORY]
  exit /b 2
)
if "%~2"=="" (
  echo Usage: run_portable.bat CONFIG_JSON INPUT_DIRECTORY [OUTPUT_DIRECTORY]
  exit /b 2
)
set OUT=%~3
if "%OUT%"=="" set OUT=output_portable
python portable_runner.py --config "%~1" --input "%~2" --output "%OUT%"

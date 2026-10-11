@echo off
setlocal
if "%~2"=="" (
  echo Usage: run_validate.bat CONFIG_JSON INPUT_DIRECTORY [OUTPUT_DIRECTORY]
  exit /b 2
)
set OUT=%~3
if "%OUT%"=="" set OUT=output_validation
python portable_runner.py --config "%~1" --input "%~2" --output "%OUT%" --validate-only

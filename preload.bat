@echo off
setlocal enabledelayedexpansion

REM Directory containing preload.bat and load.py
set "SCRIPT_DIR=%~dp0"

REM Arguments from Popen
set "REAL_EXE=%~1"
set "FILE_PATH=%~2"

if "%FILE_PATH%"=="" (
    echo Missing file_path argument
    exit /b 1
)

if "%REAL_EXE%"=="" (
    echo Missing exe_path argument
    exit /b 1
)


set "NUKE_PATH=%SCRIPT_DIR%"

"%REAL_EXE%" "%FILE_PATH%"
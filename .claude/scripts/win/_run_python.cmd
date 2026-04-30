@echo off
REM Helper interno: encuentra Python (python o python3) y ejecuta el script Python pasado.
REM Uso: _run_python.cmd <relative_script_from_scripts_dir.py> [args...]
REM Llamado por los wrappers .cmd individuales.
SETLOCAL ENABLEDELAYEDEXPANSION

SET SCRIPT_NAME=%~1
IF "%SCRIPT_NAME%"=="" (
    echo ERROR: _run_python.cmd requires script name as first arg 1>&2
    exit /b 99
)
SHIFT

REM Build path: scripts/win/_run_python.cmd → scripts/<SCRIPT_NAME>
SET WIN_DIR=%~dp0
SET PY_SCRIPT=%WIN_DIR%..\%SCRIPT_NAME%

REM Find Python
SET PY_CMD=
WHERE python >nul 2>&1
IF %ERRORLEVEL%==0 (SET PY_CMD=python) ELSE (
    WHERE python3 >nul 2>&1
    IF !ERRORLEVEL!==0 (SET PY_CMD=python3) ELSE (
        echo ERROR: Python not found in PATH. Install Python 3.9+ from python.org or Microsoft Store. 1>&2
        exit /b 99
    )
)

REM Forward all remaining args (max 9 supported via %~2..%~9; %* doesn't survive SHIFT)
%PY_CMD% "%PY_SCRIPT%" %2 %3 %4 %5 %6 %7 %8 %9
exit /b %ERRORLEVEL%

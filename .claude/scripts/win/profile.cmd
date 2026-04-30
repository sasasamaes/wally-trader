@echo off
REM Windows wrapper for profile.py — invoked as `bash .claude/scripts/win/profile.cmd <args>`
REM   from slash commands (works because Windows has Git Bash) OR direct cmd usage.
REM Equivalent to `bash .claude/scripts/profile.sh <args>` on macOS/Linux.
REM Usage examples:
REM   profile.cmd get          ← prints active profile name
REM   profile.cmd show         ← name + timestamp
REM   profile.cmd set retail   ← switch profile
REM   profile.cmd stale        ← exit code 0 if >12h old, 1 if fresh
REM   profile.cmd validate     ← exit code 0 + "OK: name", else error
SET SCRIPT_DIR=%~dp0
SET PYTHON_SCRIPT=%SCRIPT_DIR%..\profile.py

REM Try python (Windows default), fallback to python3 (rare on Win but covers WSL)
where python >nul 2>&1
IF %ERRORLEVEL%==0 (
    python "%PYTHON_SCRIPT%" %*
) ELSE (
    where python3 >nul 2>&1
    IF %ERRORLEVEL%==0 (
        python3 "%PYTHON_SCRIPT%" %*
    ) ELSE (
        echo ERROR: Python not found in PATH. Install Python 3.9+ from python.org or Microsoft Store. 1>&2
        exit /b 99
    )
)

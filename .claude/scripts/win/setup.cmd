@echo off
REM Wally Trader Windows setup launcher
REM Equivalente a: python setup.py [--check|--quick]
SET ROOT_DIR=%~dp0..\..\..
WHERE python >nul 2>&1
IF %ERRORLEVEL%==0 (
    python "%ROOT_DIR%\setup.py" %*
) ELSE (
    WHERE python3 >nul 2>&1
    IF %ERRORLEVEL%==0 (
        python3 "%ROOT_DIR%\setup.py" %*
    ) ELSE (
        echo ERROR: Python no encontrado. Install desde python.org o Microsoft Store. 1>&2
        echo Importante: marca "Add Python to PATH" durante instalación. 1>&2
        exit /b 99
    )
)

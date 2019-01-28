@ECHO off
SETLOCAL


REM Set environment variables.
SET TABPY_ROOT=%CD%

REM Install requirements using Python setup tools.
ECHO Installing any missing dependencies...
CD %TABPY_ROOT%\tabpy-server
python setup.py install>install.log 2>&1
CD %TABPY_ROOT%\tabpy-tools
python setup.py install>install.log 2>&1
CD %TABPY_ROOT%

SET INSTALL_LOG_MESSAGE=    Check %TABPY_ROOT%\tabpy-server\install.log for details.
IF %ERRORLEVEL% NEQ 0 (
    IF %CD% NEQ %TABPY_ROOT% (
        CD %TABPY_ROOT%
    )
    ECHO     failed
    ECHO %INSTALL_LOG_MESSAGE%
    GOTO:ERROR
) ELSE (
    ECHO     success
    ECHO %INSTALL_LOG_MESSAGE%
)


REM Parse optional CLI arguments: port and config.
ECHO Parsing parameters...
SET STARTUP_CMD=python tabpy.py
IF [%1] NEQ [] (
    ECHO     Using config file at %TABPY_ROOT%\tabpy-server\tabpy_server\%1
    SET STARTUP_CMD=%STARTUP_CMD% --config=%1
)


REM Start TabPy server.
ECHO Starting TabPy server...
ECHO;
CD %TABPY_ROOT%\tabpy-server\tabpy_server
%STARTUP_CMD%
CD %TABPY_ROOT%
IF %ERRORLEVEL% NEQ 0 (
    ECHO      Failed to start TabPy server.
    GOTO:ERROR
)


GOTO:SUCCESS


REM Exit with error
:ERROR
    ENDLOCAL
    EXIT /B 1


REM All succeeded
:SUCCESS
    EXIT /B %ERRORLEVEL%
    ENDLOCAL

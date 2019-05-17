@ECHO off
SETLOCAL


REM Set environment variables.
SET TABPY_ROOT="%CD%"
SET INSTALL_LOG=%TABPY_ROOT%\tabpy-server\install.log
SET SAVE_PYTHONPATH=%PYTHONPATH%
SET MIN_PY_VER=3.6
SET DESIRED_PY_VER=3.6.5


ECHO Checking for presence of Python in the system path variable.
SET PYTHON_ERROR=Fatal Error : TabPy startup failed. Check that Python 3.6.5 or higher is installed and is in the system PATH environment variable.
python --version
IF %ERRORLEVEL% NEQ 0 (
    ECHO %PYTHON_ERROR%
    SET RET=1
    GOTO:END
) ELSE (
    FOR /F "TOKENS=2" %%a IN ('python --version 2^>^&1') DO (
        IF %%a LSS %MIN_PY_VER% (
            ECHO %PYTHON_ERROR%
            SET RET=1
            GOTO:END
        ) ELSE IF %%a LSS %DESIRED_PY_VER% (
            ECHO Warning : Python %%a% is not supported. Please upgrade Python to 3.6.5 or higher.
            SET RET=1
        )
    )
)

REM Install requirements using Python setup tools.
ECHO Installing any missing dependencies...

CD %TABPY_ROOT%\tabpy-server
ECHO Installing tabpy-server dependencies...>%INSTALL_LOG%	
python setup.py install>>%INSTALL_LOG% 2>&1

CD %TABPY_ROOT%\tabpy-tools
ECHO: >> %INSTALL_LOG%
ECHO Installing tabpy-tools dependencies...>>%INSTALL_LOG%
python setup.py install>>%INSTALL_LOG% 2>&1

CD %TABPY_ROOT%
SET INSTALL_LOG_MESSAGE=    Check %INSTALL_LOG% for details.
IF %ERRORLEVEL% NEQ 0 (
    CD %TABPY_ROOT%
    ECHO     failed
    ECHO %INSTALL_LOG_MESSAGE%
    SET RET=1
    GOTO:END
) ELSE (
    ECHO     success
    ECHO %INSTALL_LOG_MESSAGE%
)


REM Parse optional CLI arguments: config file
ECHO Parsing parameters...
SET PYTHONPATH=.\tabpy-server;.\tabpy-tools;%PYTHONPATH%
SET STARTUP_CMD=python tabpy-server\tabpy_server\tabpy.py
IF [%1] NEQ [] (
    ECHO     Using config file at %1
    SET STARTUP_CMD=%STARTUP_CMD% --config=%1
)


ECHO Starting TabPy server...
ECHO;
%STARTUP_CMD%
IF %ERRORLEVEL% NEQ 0 (
    ECHO      Failed to start TabPy server.
    SET RET=1
    GOTO:END
)


SET RET=%ERRORLEVEL%
GOTO:END


:END
    SET PYTHONPATH=%SAVE_PYTHONPATH%
    CD %TABPY_ROOT%
    EXIT /B %RET%
    ENDLOCAL

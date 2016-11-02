@IF [%1]==[] ( 
set port=9004
) ELSE (
set port=%1
)
@SET CurrentPath="%~dp0"
@ECHO Server will be initialized using port: %port%
@SET CONDA_ENVIRONMENT=Tableau-Python-Server
@REG Query "HKLM\Hardware\Description\System\CentralProcessor\0" | find /i "x86" > NUL && set OS=32BIT || set OS=64BIT
@ECHO.
@ECHO ~~~~~~~~~~~~~~~~  Looking for existing Anaconda installation  ~~~~~~~~~~~~~~~~~
@ECHO.
@SET CONDACMD=""
@SET ACMD=""
@ECHO OFF
SET ANACONAREGKEY=Anaconda_*
@IF EXIST %UserProfile%\Anaconda\Scripts\conda.exe SET CONDACMD=%UserProfile%\Anaconda\Scripts
@IF %CONDACMD%=="" FOR /f %%p in ('where anaconda.bat /f') do SET CONDACMD=%%p
@IF %CONDACMD%=="" FOR /f %%z in ('REG Query HKU /k /s /f %ANACONAREGKEY%') DO IF %%z NEQ End SET ACMD=%%z
@IF %CONDACMD%=="" IF NOT %ACMD%=="" SET ACMD=%ACMD:HKEY_USERS=HKU%\InstallPath
@IF %CONDACMD%=="" IF NOT %ACMD%=="" FOR /f "tokens=1,3" %%a in ('REG Query %ACMD%') DO IF %%a==(Default) SET CONDACMD=%%b\Scripts
SET CONDACMD=%CONDACMD:\anaconda.bat=%
@IF EXIST %CONDACMD%\anaconda.bat (
@ECHO Existing Anaconda installation found.
) ELSE (
@ECHO No existing Anaconda installation found.
@ECHO Looking for a local installer...
IF EXIST "%~dp0\Anaconda-Installer.exe" (
@ECHO.
@ECHO ~~~~~~~~~~~~~~~~  Installing Anaconda from existing installer  ~~~~~~~~~~~~~~~~
@ECHO                          This may take a few minutes
@ECHO.
) ELSE (
@ECHO.
@ECHO ~~~~~~~~~~~~~~~~~~~~  Downloading and installing Anaconda  ~~~~~~~~~~~~~~~~~~~~
@ECHO                           This may take a few minutes
@ECHO.
@IF %OS%==64BIT powershell -Command "Import-Module BitsTransfer; Start-BitsTransfer https://repo.continuum.io/archive/Anaconda-2.3.0-Windows-x86_64.exe $PWD\Anaconda-Installer.exe"
@IF %OS%==32BIT powershell -Command "Import-Module BitsTransfer; Start-BitsTransfer https://repo.continuum.io/archive/Anaconda-2.3.0-Windows-x86.exe $PWD\Anaconda-Installer.exe"
@ECHO Download completed.
)
@ECHO Installing Anaconda...
@start /wait "" Anaconda-Installer.exe /InstallationType=JustMe /RegisterPython=0 /S /D=%UserProfile%\Anaconda
IF %CONDACMD%=="" SET CONDACMD=%UserProfile%\Anaconda\Scripts
)
@ECHO.
@ECHO ~~~~~~~~~~~~~~~~~~~~~~~~  Activating the environment  ~~~~~~~~~~~~~~~~~~~~~~~~~
@ECHO.
@IF NOT EXIST "%CONDACMD%\conda.exe" (
@CD "%CONDACMD%"
@CD ..\..\..
@SET "CONDACMD=%CD%\Scripts"
@CD %CurrentPath%
)
@SET PATH=%PATH%;%CONDACMD%
@IF NOT EXIST %CONDACMD:Scripts=envs%\%CONDA_ENVIRONMENT% (
@ECHO No %CONDA_ENVIRONMENT% environment found. Creating one...
@conda create --yes --name %CONDA_ENVIRONMENT% --clone root
 ) ELSE (
@ECHO Found existing %CONDA_ENVIRONMENT% environment.
@ECHO %CONDACMD:Scripts=envs%\%CONDA_ENVIRONMENT%
 )
@CALL %CONDACMD%\activate %CONDA_ENVIRONMENT%
@SET PYTHONPATH=%PYTHONPATH%;%CONDACMD:Scripts=envs%\%CONDA_ENVIRONMENT%\Scripts
@ECHO.
@ECHO ~~~~~~~~~~~~~~~~~~~~~~~~~~  Installing dependencies  ~~~~~~~~~~~~~~~~~~~~~~~~~~
@ECHO.
@CD %CurrentPath%
pip install -r ./tabpy-server/requirements.txt
pip install ./tabpy-client
pip install ./tabpy-server
@SET STARTUPBAT=%CONDACMD:Scripts=envs%\%CONDA_ENVIRONMENT%\Lib\site-packages\tabpy_server\startup.bat
@SET TABPY_STATE_PATH=%CONDACMD:Scripts=envs%\%CONDA_ENVIRONMENT%\Lib\site-packages\tabpy_server
@IF EXIST %STARTUPBAT% (
@ECHO. 
@ECHO ~~~~~~~~~~~~~~~~~~~~~~~~~~~  Installation complete  ~~~~~~~~~~~~~~~~~~~~~~~~~~~
@ECHO.
@ECHO.
@ECHO From now on, you can start the server by running %STARTUPBAT%
@ECHO.
@ECHO.
@CD %TABPY_STATE_PATH%
@ECHO Starting the server for the first time...
@ECHO.
@ECHO.
@IF NOT EXIST "%TABPY_STATE_PATH%\state.ini" @copy "%TABPY_STATE_PATH%\state.ini.template"  "%TABPY_STATE_PATH%\state.ini"
@SET PYTHONPATH=%PYTHONPATH%;%TABPY_STATE_PATH%
@python "%TABPY_STATE_PATH%\tabpy.py" --port %port%
)
IF NOT EXIST %STARTUPBAT% (
@ECHO. 
@ECHO ~~~~~~~~~~~~~~~~~~~~~~~~~~~~  Installation failed  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@ECHO.
)

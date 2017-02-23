@IF [%1]==[] ( 
set port=9004
) ELSE (
set port=%1
)
@SET CONDA_ENVIRONMENT=Tableau-Python-Server
@SET SETUP_PATH="%~dp0"
@CD %SETUP_PATH%
@CD ..\..\..\..\..\
@IF EXIST %CD%\Scripts (
@CD Scripts
@CALL activate %CONDA_ENVIRONMENT%
) ELSE (
@CD %SETUP_PATH%
@CD ..\..\..\
@SET PYTHONPATH=%PYTHONPATH%;%CD%
)
@CD %SETUP_PATH%
@SET TABPY_STATE_PATH=%CD%
@IF NOT EXIST state.ini (
@copy state.ini.template state.ini
)
@python tabpy.py --port %port%

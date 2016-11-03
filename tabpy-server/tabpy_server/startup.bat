@IF [%1]==[] ( 
set port=9004
) ELSE (
set port=%1
)
@SET CONDA_ENVIRONMENT=Tableau-Python-Server
@SET SETUP_PATH="%~dp0"
@CD %SETUP_PATH%
@CD ..\..\..\..\..\
@CD Scripts
@CALL activate %CONDA_ENVIRONMENT%
@CD %SETUP_PATH%
SET TABPY_STATE_PATH=%CD%
@IF NOT EXIST state.ini (
@copy state.ini.template state.ini
)
@set PYTHONPATH=%PYTHONPATH%;%SETUP_PATH%
python tabpy.py --port %port%

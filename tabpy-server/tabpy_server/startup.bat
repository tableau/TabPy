@IF [%1]==[] ( 
set port=9004
) ELSE (
set port=%1
)
@SET CONDA_ENVIRONMENT=Tableau-Python-Server
@SET TABPY_STATE_PATH=%CD%
@CD ..\..\..
@CD Scripts
@call activate %CONDA_ENVIRONMENT%

@IF NOT EXIST %TABPY_STATE_PATH%\state.ini (
@copy %TABPY_STATE_PATH%\state.ini.template %TABPY_STATE_PATH%\state.ini
)

@set PYTHONPATH=%PYTHONPATH%;%TABPY_STATE_PATH%
python %TABPY_STATE_PATH%/tabpy.py --port %port%







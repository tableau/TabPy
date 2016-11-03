CONDA_ENVIRONMENT=Tableau-Python-Server
SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
CONDA_DEFAULT_ENV=$CONDA_ENVIRONMENT
export TABPY_STATE_PATH=$SCRIPT_DIR
cd "$TABPY_STATE_PATH"
cd "../../../../"
export PATH="$PWD"/bin:$PATH
export PYTHONPATH=$PYTHONPATH:"$PWD"/lib/python2.7
source activate $CONDA_ENVIRONMENT
if [ "$#" -ne 1 ] ; then
  PORT=9004
else
  PORT=$1
fi
# Checking for an existing state file, using a template if not found
if [ -e "$SCRIPT_DIR/state.ini" ]; then
  echo "Found existing state.ini"
else
  cp "$SCRIPT_DIR"/state.ini.template "$SCRIPT_DIR"/state.ini
  echo "Using initial state.ini"
fi
python "$SCRIPT_DIR"/tabpy.py --port $PORT

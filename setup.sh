# This will be created or re-used if exist:
CONDA_ENVIRONMENT=Tableau-Python-Server

# This is needed to find dependent files that are in the same folder as the script
SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
CONDACMD="$(which conda)"


# this is needed by the server process (hence export)
export TABPY_STATE_PATH=$PWD

if [ "$#" -ne 1 ] ; then
  PORT=9004
else
  PORT=$1
fi


function download_file {
  # detect wget
  echo "Downloading $2 from $1 ..."
  # if it is a file
  download_file_result=0
  if [ -e $1 ] ; then
    cp $1 $2
    return
  fi
  if [ -z `which wget` ] ; then
    if [ -z `which curl` ] ; then
      echo "Unable to find either curl or wget! Cannot proceed with
            automatic install."
      exit 1
    fi
    # -f makes it fail on no status code
    curl -f $1 -o $2 || download_file_result=$?
  else
    wget $1 -O $2 || download_file_result=$?
  fi
  # wget leaves stuff lying around even if the download failed
  if [ $download_file_result -ne 0 ]; then
    rm -f $2
  fi
} # end of download file



echo "~~~~~~~~~~~~~~~  Downloading and installing Anaconda  ~~~~~~~~~~~~~~~"


# install anaconda if not already available
if [ -z `which conda` ] ; then
  if [[ ! -e anaconda ]]; then
    conda_download=""
    if [[ $OSTYPE == linux* ]]; then
            echo "Linux detected"
            conda_download="repo.continuum.io/archive/Anaconda-2.3.0-Linux-x86_64.sh"
            conda_ext=".sh"
    elif [[ $OSTYPE == darwin* ]]; then
            echo "Mac detected"
            conda_download="repo.continuum.io/archive/Anaconda-2.3.0-MacOSX-x86_64.sh"
            conda_ext=".sh"
    else
            echo "Unsupported Operating System"
            exit 1
    fi

    conda_download="https://$conda_download"

    if [[ ! -e "anaconda$conda_ext" ]]; then
      echo "Trying to download anaconda"
      download_file $conda_download "anaconda$conda_ext"
      if [ $download_file_result -ne 0 ]; then
              echo "Unable to download anaconda installation"
              exit 1
      fi
      bash anaconda.sh -p $HOME/anaconda -b
      CONDACMD=$HOME/anaconda/bin/conda
    else
      echo "Anaconda installed already."
    fi
  fi
  else
    echo "Anaconda installed already."
fi

# step out of any other environment that is currently active to root
source activate root
CONDAFOLDER="$( dirname "$(which conda)" )"
cd "$CONDAFOLDER"
cd ".."

echo "~~~~~~~~~~~~~~~  Activating the environment  ~~~~~~~~~~~~~~~"

if [ ! -e "$PWD/envs/$CONDA_ENVIRONMENT" ]; then
  echo "Conda env '$CONDA_ENVIRONMENT' doesn't exist, creating now."
  $CONDACMD create --yes -n $CONDA_ENVIRONMENT --clone root
else
  echo "Conda env '$CONDA_ENVIRONMENT' already exists."
fi

# activate that environment
  export ANACONDA_ENVS=$PWD/envs
  export CONDA_DEFAULT_ENV=$CONDA_ENVIRONMENT
  export CONDA_ENV_PATH=$PWD/envs
  export PATH=$PWD/envs/$CONDA_ENVIRONMENT:$PATH
  source activate $CONDA_ENVIRONMENT

# We need this for Python to find other .py files in the server folder
  export PYTHONPATH=$PYTHONPATH:$SCRIPT_DIR

echo "~~~~~~~~~~~~~~~  Installing dependencies  ~~~~~~~~~~~~~~~"

pip install -r "$SCRIPT_DIR"/tabpy-server/requirements.txt
pip install "$SCRIPT_DIR"/tabpy-client
pip install "$SCRIPT_DIR"/tabpy-server

STARTUPPATH="$PWD/envs/$CONDA_ENVIRONMENT/lib/python2.7/site-packages/tabpy_server"
if [ ! -f "$STARTUPPATH/startup.sh" ]; then
  echo "~~~~~~~~~~~~~~~~~  Installation failed  ~~~~~~~~~~~~~~~~"
else
  echo "~~~~~~~~~~~~~~~  Installation completed  ~~~~~~~~~~~~~~~"
  echo
  echo "From now on, you can start the server by running $STARTUPPATH/startup.sh"
  echo
  echo
  echo "Starting the server for the first time..."
  bash "$STARTUPPATH/startup.sh" $PORT
fi

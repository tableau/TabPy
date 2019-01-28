#!/bin/bash

function check_status() {
    if [ $? -ne 0 ]; then
        echo TabPy startup failed.
        exit 1
    fi
}

# Set environment variables
echo Setting TABPY_ROOT to current working directory.
export TABPY_ROOT=$PWD

# Check for dependencies, install them if they're not present.
echo Installing TabPy-server requirements.
echo Read the logs at $TABPY_ROOT/tabpy-server/install.log
cd $TABPY_ROOT/tabpy-server
python3 setup.py install &> install.log
cd $TABPY_ROOT/tabpy-tools
python3 setup.py install &> install.log
cd $TABPY_ROOT
check_status

# Check for CLI parameters
echo Parsing command line parameters...
while getopts ":p:c:" opt; do
    case $opt in
        p) PORT="$OPTARG"
        ;;
        c) CONFIG="$OPTARG"
        ;;
        \?) echo "Invalid option -$OPTARG" >&2
        ;;
    esac
done

if [ ! -z $PORT ]; then
    echo Using port $PORT.
fi
if [ ! -z $CONFIG ]; then
    echo Using the config file at $TABPY_ROOT/tabpy-server/$CONFIG.
fi

# Start TabPy server
echo
echo Starting TabPy server...
cd $TABPY_ROOT/tabpy-server/tabpy_server
if [ -z $PORT ] && [ -z $CONFIG ]; then
    echo Using default parameters.
    python3 tabpy.py
elif [ -z $CONFIG ]; then
    python3 tabpy.py --port=$PORT
elif [ -z $PORT ]; then
    python3 tabpy.py --config=$CONFIG
else
    python3 tabpy.py --port=$PORT --config=$CONFIG
fi
cd $TABPY_ROOT

check_status
exit 0

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
export INSTALL_LOG=$TABPY_ROOT/tabpy-server/install.log

# Check for dependencies, install them if they're not present.
echo Installing TabPy-server requirements.
echo Read the logs at $INSTALL_LOG

cd $TABPY_ROOT/tabpy-server
echo -e "\nInstalling tabpy-server dependencies..." > $INSTALL_LOG
python3 setup.py install >> $INSTALL_LOG 2>&1
check_status

cd $TABPY_ROOT/tabpy-tools
echo -e "\nInstalling tabpy-tools dependencies..." >> $INSTALL_LOG
python3 setup.py install >> $INSTALL_LOG 2>&1
check_status

cd $TABPY_ROOT
check_status

# Check for CLI parameters
echo Parsing command line parameters...
while getopts ":c:" opt; do
    case $opt in
        c) CONFIG="$OPTARG"
        ;;
        \?) echo "Invalid option -$OPTARG" >&2
        ;;
    esac
done

if [ ! -z $CONFIG ]; then
    echo Using the config file at $TABPY_ROOT/tabpy-server/$CONFIG.
fi

# Exit if in a test environent
if [ ! -z $TEST_ENV ]; then
    echo Detected testing environment. Exiting successfully.
	exit 0
fi

# Start TabPy server
echo
echo Starting TabPy server...
if [ -z $CONFIG ]; then
    echo Using default parameters.
    python3 tabpy-server/tabpy.py
else
    python3 tabpy-server/tabpy.py --config=$CONFIG
fi

check_status
exit 0

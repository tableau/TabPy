#!/bin/bash

function check_status() {
    if [ $? -ne 0 ]; then
        echo TabPy startup failed. $1
        exit 1
    fi
}

# Check for Python in PATH
echo Checking for presence of Python in the system path variable.
python --version &>-
check_status "Cannot find Python.  Check that Python is installed and is in the system PATH environment variable."

# Setting local variables
echo Setting TABPY_ROOT to current working directory.
TABPY_ROOT=$PWD
INSTALL_LOG=${TABPY_ROOT}/tabpy-server/install.log

# Check for dependencies, install them if they're not present.
echo Installing TabPy-server requirements.
echo Read the logs at ${INSTALL_LOG}

cd ${TABPY_ROOT}/tabpy-server
echo -e "\nInstalling tabpy-server dependencies..." > ${INSTALL_LOG}
python3 setup.py install >> ${INSTALL_LOG} 2>&1
check_status

cd ${TABPY_ROOT}/tabpy-tools
echo -e "\nInstalling tabpy-tools dependencies..." >> ${INSTALL_LOG}
python3 setup.py install >> ${INSTALL_LOG} 2>&1
check_status

cd ${TABPY_ROOT}
check_status

# Check for CLI parameters
for i in "$@"
do
case $i in
	-c=*|--config=*)
	CONFIG="${i#*=}"
	shift
	;;
	--no-startup)
	TEST_ENV=true
	shift
	;;
	*)
	echo Invalid option: $i
esac
done

if [ ! -z ${CONFIG} ]; then
    echo Using the config file at ${TABPY_ROOT}/tabpy-server/$CONFIG.
fi

# Exit if in a test environent
if [ ! -z ${TEST_ENV} ]; then
    echo Skipping server startup. Exiting successfully.
	exit 0
fi

# Start TabPy server
echo
echo Starting TabPy server...
SAVE_PYTHONPATH=$PYTHONPATH
export PYTHONPATH=${TABPY_ROOT}/tabpy-server:${TABPY_ROOT}/tabpy-tools:$PYTHONPATH
if [ -z $CONFIG ]; then
    echo Using default parameters.
    python3 tabpy-server/tabpy_server/tabpy.py
else
    python3 tabpy-server/tabpy_server/tabpy.py --config=$CONFIG
fi

export PYTHONPATH=$SAVE_PYTHONPATH
check_status
exit 0

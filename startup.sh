#!/bin/bash

min_py_ver=3.6
desired_py_ver=3.6.5

function check_status() {
    if [ $? -ne 0 ]; then
        echo $1
        exit 1
    fi
}

function check_python_version() {
    python3 --version
    check_status $1

    py_ver=($(python3 --version 2>&1) \| tr ' ' ' ')
    if [ "${py_ver[1]}" \< "$min_py_ver" ]; then
        echo Fatal Error : $1
        exit 1
    elif [ "${py_ver[1]}" \< "$desired_py_ver" ]; then
        echo Warning : Python ${py_ver[1]} is not supported. Please upgrade Python to 3.6.5 or higher.
    fi
}

function install_dependencies() {
    # $1 = tabpy_server | tabpy_tools
    # $2 = true if install logs are printed to the console,
    #      false if they are printed to a log file
    # $3 = install log file path
    if [ "$2" = true ]; then
        echo -e "\nInstalling ${1} dependencies..."
        python3 setup.py install
    elif [ "$2" = false ]; then
        echo -e "\nInstalling ${1} dependencies..." >> "${3}"
        python3 setup.py install >> "${3}" 2>&1
    else
        echo Invalid startup environment.
        exit 1
    fi
    check_status "Cannot install dependencies."
}

# Check for Python in PATH
echo Checking for presence of Python in the system path variable.
check_python_version "TabPy startup failed. Check that Python 3.6.5 or higher is installed and is in the system PATH environment variable."

# Setting local variables
echo Setting TABPY_ROOT to current working directory.
TABPY_ROOT="$PWD"
INSTALL_LOG="${TABPY_ROOT}/tabpy-server/install.log"
echo "" > "${INSTALL_LOG}"
PRINT_INSTALL_LOGS=false

# Parse CLI parameters
for i in "$@"
do
    case $i in
        -c=*|--config=*)
        CONFIG="${i#*=}"
        shift
        ;;
        --no-startup)
        NO_STARTUP=true
        shift
        ;;
        --print-install-logs)
        PRINT_INSTALL_LOGS=true
        shift
        ;;
        *)
        echo Invalid option: $i
    esac
done

# Check for dependencies, install them if they're not present.
echo Installing TabPy-server requirements.
if [ "$PRINT_INSTALL_LOGS" = false ]; then
    echo Read the logs at ${INSTALL_LOG}
fi

cd "${TABPY_ROOT}/tabpy-server"
install_dependencies "tabpy-server" ${PRINT_INSTALL_LOGS} ${INSTALL_LOG}

cd "${TABPY_ROOT}/tabpy-tools"
install_dependencies "tabpy-tools" ${PRINT_INSTALL_LOGS} ${INSTALL_LOG}

cd "${TABPY_ROOT}"
check_status

if [ ! -z ${CONFIG} ]; then
    echo Using the config file at ${TABPY_ROOT}/tabpy-server/$CONFIG.
fi

# Exit if in a test environent
if [ ! -z ${NO_STARTUP} ]; then
    echo Skipping server startup. Exiting successfully.
	exit 0
fi

# Start TabPy server
echo
echo Starting TabPy server...
SAVE_PYTHONPATH=$PYTHONPATH
export PYTHONPATH="${TABPY_ROOT}/tabpy-server:${TABPY_ROOT}/tabpy-tools:$PYTHONPATH"
if [ -z $CONFIG ]; then
    echo Using default parameters.
    python3 tabpy-server/tabpy_server/tabpy.py
else
    python3 tabpy-server/tabpy_server/tabpy.py --config=$CONFIG
fi

export PYTHONPATH=$SAVE_PYTHONPATH
check_status
exit 0

#TabPy Server

TabPy server is the server component of Tableau's Python integration. It is a Python process built on Tornado and other Python libraries.

##Setup on Linux/MacOS

On a Linux-based system you can use the script `setup.sh` to install TabPy from scratch. 

Start by clicking on the green **clone or download** button in the upper right corner on TabPy repository landing page and downloading the zip file. After unzipping, navigate to the folder containing `setup.sh` in a Terminal window and type `./setup.sh`.

On MacOSX you may need to also give permissions to the file by typing the following: `chmod +x setup.sh`

The script does the following:

  - Downloads and installs Anaconda, unless Anaconda is in the PATH or a folder `Anaconda` is found in the current folder. Anaconda provides an exhaustive set of Python packages, including ML-related libraries that can be used by Python code executed by the server.
  - Creates a Python environment named `Tableau-Python-Server` if one doesn't already exist. The script then activates the environment and adds the server folder to the PYTHONPATH (which is necessary for the server script to find its Python dependencies in the same folder).
  - Installs required Python packages into the new environment, as well as the client package, as it contains common functionality that the server depends on.
  - Initializes the server, displays the install location and instructions on how to start the server next time.

After setup completes or when you run `startup.sh` per the instructions to start the server, you should see an output like this:

```bash

INFO:__main__:{"INFO": "Loading state from state file"}
INFO:__main__:{"INFO": "Initializing tabpy"}
INFO:__main__:{"INFO": "Done initializing tabpy"}
INFO:__main__:{"INFO": "Web service listening on port 9004"}

```

At this point the server is ready to execute Python code remotely, or to deploy Python functions. See the [client documentation](client.md) for instructions on how to deploy Python functions.

You can stop the server simply by terminating the process (for example, with CTRL-C).


##Setup on Windows
On Windows you can use the script `setup.bat` to install TabPy from scratch. 

Start by clicking on the green **clone or download** button in the upper right corner on TabPy repository landing page and downloading the zip file. After unzipping, navigate to the folder containing `setup.bat` using Windows command line and type `setup.bat`. 

The script carries out the following steps:

  - Downloads and installs Anaconda, under the current user account for example `C:\users\yourUserName\` unless Anaconda is in the PATH or has a registry entry. Anaconda provides an exhaustive set of Python packages, including ML-related libraries that can be used by Python code executed by the server.
  - Creates a Python environment named `Tableau-Python-Server` if one doesn't already exist. The script then activates the environment.
  - Installs the required Python packages into the new environment, as well as the client package, as it contains common functionality that the server depends on.
  - Initializes the server, displays the install location and instructions on how to start the server next time.

After setup completes or when you run `startup.bat` per the instructions to start the server, you should see an output like this:

```bash

INFO:__main__:{"INFO": "Loading state from state file"}
INFO:__main__:{"INFO": "Initializing tabpy"}
INFO:__main__:{"INFO": "Done initializing tabpy"}
INFO:__main__:{"INFO": "Web service listening on port 9004"}

```

At this point the server is ready to execute Python code remotely, or to deploy Python functions. See the [client documentation](client.md) for instructions on how to deploy Python functions.

You can stop the server simply by terminating the python2.7 process which can be seen in Windows Task Manager. (Press Ctrl+Shift+Esc to access Task Manager)


##Manual Installation

If you are familiar with Python environments and have already set one up or prefer not to use Anaconda and just want to start the server process, you can skip the setup script, install the dependencies and run the process directly from the command line. The manual  installation instructions assume either Conda or Python are defined as part of PATH.

It is optional but recommended you create a new Conda environment for this project:

```Batchfile

conda create --name Tableau-Python-Server python=2.7 anaconda

```

The example above creates a Python 2.7 environment but Tableau Python Server is supported on both Python 2.7+ and Python 3.5+.

Now activate the newly created environment.

On Linux/MacOS:

```bash

source activate Tableau-Python-Server

```

On Windows:

```Batchfile

activate Tableau-Python-Server

```

Since TabPy is available on [PyPI](https://pypi.python.org/pypi/tabpy-server) you can install by simply running the following command.


```Batchfile

pip install tabpy-server

```

As the packages are installed, you will see the install locations listed in the command line. These might look like `/Users/username/anaconda/envs/Tableau-Python-Server/lib/python2.7/site-packages` or `\Users\username\anaconda\envs\Tableau-Python-Server\lib\site-packages` depending on your environment.

Navigate to the tabpy_server folder under `site-packages` and run `startup.bat` or `startup.sh` on Windows and Linux/MacOS respectively. You can specify a custom port number as an argument e.g. `startup.bat 9001`. 

##Updating TabPy
You can update to a newer version by using the `-—upgrade` option in `pip`. 

```Batchfile

pip install --upgrade tabpy-server

```

For this to be successful, if you installed TabPy in a Conda environment, make sure that it is active. 


##Extending the Environment

If your functionality depends on Python packages that are not included, you need to install them into your Python environment to make them available to the server process. 

The following code snippet assumes you have already run `setup.sh` or `setup.bat`, which created a Conda environment and started the server process in that environment. 

By adding the package _names_ to it, it becomes available for any Python code to be executed in the server:

On Linux/MacOS:

```bash

/Anaconda/bin/source activate Tableau-Python-Server
pip install _names_of_packages_here_

```
On Windows:

```Batchfile

/Anaconda/Scripts/activate Tableau-Python-Server
pip install _names_of_packages_here_

```
If you installed TabPy without Anaconda in your default Python framework you can achieve the same by doing:

```Batchfile

pip install _names_of_packages_here_

```

You can do this in a separate terminal while the server process is running-no need to restart.


##REST Interfaces

The server process exposes several REST APIs to get status and to execute Python code and query deployed methods.


###http:get:: /info

Get static information about the server.

Example request:

```HTTP

    GET /info HTTP/1.1
    Host: localhost:9004
    Accept: application/json

```

Example response:

```HTTP

    HTTP/1.1 200 OK
    Content-Type: application/json

    {"description": "",
     "creation_time": "0",
     "state_path": "/Users/username/my-server-state-folder",
     "server_version": "dev",
     "name": "my-server-name"}

```

  - `description` is a string that is hardcoded in the `state.ini` file and can be edited there.
  - `creation_time` is the creation time in seconds since 1970-01-01, hardcoded in the `state.ini` file, where it can be edited.
 - `state_path` is the state file path of the server (the value of the environment variable TABPY_STATE_PATH at the time the server was started).
  - `server_version` is a hardcoded string provided by the server (defined in `server/common/config.py`). Clients can use this information for compatibility checks.


Using curl:

```bash

    curl -X GET http://localhost:9004/info

```

###http:get:: /status

Gets runtime status of deployed endpoints. If no endpoints are deployed in the server, the returned data is an empty JSON object.

Example request:

```HTTP

    GET /status HTTP/1.1
    Host: localhost:9004
    Accept: application/json

```

Example response:

```HTTP

    HTTP/1.1 200 OK
    Content-Type: application/json

    {"clustering": {
      "status": "LoadSuccessful",
      "last_error": null,
      "version": 1,
      "type": "model"},
     "add": {
      "status": "LoadSuccessful",
      "last_error": null,
      "version": 1,
      "type": "model"}
    }

```

Using curl:

```bash

    curl -X GET http://localhost:9004/status

```


###http:get:: /endpoints

Gets a list of deployed endpoints and their static information. If no endpoints are deployed in the server, the returned data is an empty JSON object.

Example request:

```HTTP

    GET /endpoints HTTP/1.1
    Host: localhost:9004
    Accept: application/json

```

Example response:

```HTTP

    HTTP/1.1 200 OK
    Content-Type: application/json

    {"clustering":
      {"description": "",
       "docstring": "-- no docstring found in query function --",
       "creation_time": 1469511182,
       "version": 1,
       "dependencies": [],
       "last_modified_time": 1469511182,
       "type": "model",
       "target": null},
    "add": {
      "description": "",
      "docstring": "-- no docstring found in query function --",
      "creation_time": 1469505967,
      "version": 1,
      "dependencies": [],
      "last_modified_time": 1469505967,
      "type": "model",
      "target": null}
    }

```

Using curl:

```bash

    curl -X GET http://localhost:9004/endpoints

```



###http:get:: /endpoints/:endpoint

Gets the description of a specific deployed endpoint. The endpoint must first be deployed in the server (see the [client documentation](client.md)).

Example request:

```HTTP

    GET /endpoints/add HTTP/1.1
    Host: localhost:9004
    Accept: application/json

```

Example response:

```HTTP

    HTTP/1.1 200 OK
    Content-Type: application/json

    {"description": "", "docstring": "-- no docstring found in query function --",
     "creation_time": 1469505967, "version": 1, "dependencies": [],
     "last_modified_time": 1469505967, "type": "model", "target": null}

```

Using curl:

```bash

    curl -X GET http://localhost:9004/endpoints/add

```


###http:post:: /evaluate

Executes a block of Python code, replacing named parameters with their provided values.

The expected POST body is a JSON dictionary with two elements:

  - A key `data` with a value that contains the parameter values passed to the code. These values are key-value pairs, following a specific convention for key names (`_arg1`, `_arg2`, etc.).
  - A key `script` with a value that contains the Python code (one or more lines). Any references to the parameter names will be replaced by their values according to `data`.


Example request:

```HTTP

    POST /evaluate HTTP/1.1
    Host: localhost:9004
    Accept: application/json

    {"data": {"_arg1": 1, "_arg2": 2}, "script": "return _arg1+_arg2"}

```

Example response:

```HTTP

    HTTP/1.1 200 OK
    Content-Type: application/json

    3

```

Using curl:

```bash

    curl -X POST http://localhost:9004/evaluate \
    -d '{"data": {"_arg1": 1, "_arg2": 2}, "script": "return _arg1 + _arg2"}'

```

It is possible to call a deployed function from within the code block, through the predefined function `tabpy.query`. This function works like the client library's `query` method, and returns the corresponding data structure.  The function must first be deployed as an endpoint in the server (for more details see the [client documentation](client.md)).

The following example calls the endpoint `clustering` as it was deployed in the section [deploy-function](client.md#deploying-a-function):

```HTTP

    POST /evaluate HTTP/1.1
    Host: example.com
    Accept: application/json

    { "data":
      { "_arg1": [6.35, 6.40, 6.65, 8.60, 8.90, 9.00, 9.10],
        "_arg2": [1.95, 1.95, 2.05, 3.05, 3.05, 3.10, 3.15]
      },
      "script": "return tabpy.query('clustering', x=_arg1, y=_arg2)"}

```

The next example shows how to call `evaluate` from a terminal using curl; this code queries the method `add` that was deployed in the section [deploy-function](client.md#deploying-a-function):

```bash

    curl -X POST http://localhost:9004/evaluate \
    -d '{"data": {"_arg1":1, "_arg2":2},
         "script": "return tabpy.query(\"add\", x=_arg1, y=_arg2)[\"response\"]"}'

```


###http:post:: /query/:endpoint

Executes a function at the specified endpoint. The function must first be deployed (see the [client documentation](client.md)).

This interface expects a JSON body with a `data` key, specifying the values for the function, according to its original definition. In the example below, the function `clustering` was defined with a signature of two parameters `x` and `y`, expecting arrays of numbers.

Example request:

```HTTP

    POST /query/clustering HTTP/1.1
    Host: localhost:9004
    Accept: application/json

    {"data": {
      "x": [6.35, 6.40, 6.65, 8.60, 8.90, 9.00, 9.10],
      "y": [1.95, 1.95, 2.05, 3.05, 3.05, 3.10, 3.15]}}

```

Example response:

```HTTP

    HTTP/1.1 200 OK
    Content-Type: application/json

    {"model": "clustering", "version": 1, "response": [0, 0, 0, 1, 1, 1, 1],
     "uuid": "46d3df0e-acca-4560-88f1-67c5aedeb1c4"}

```

Using curl:

```bash

    curl -X GET http://localhost:9004/query/clustering -d \
    '{"data": {"x": [6.35, 6.40, 6.65, 8.60, 8.90, 9.00, 9.10],
               "y": [1.95, 1.95, 2.05, 3.05, 3.05, 3.10, 3.15]}}'

```

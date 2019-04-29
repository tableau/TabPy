# TabPy API v1

<!-- markdownlint-disable MD004 -->

<!-- toc -->

- [Authentication](#authentication)
- [http:get:: /status](#httpget-status)
- [http:get:: /endpoints](#httpget-endpoints)
- [http:get:: /endpoints/:endpoint](#httpget-endpointsendpoint)
- [http:post:: /evaluate](#httppost-evaluate)
- [http:post:: /query/:endpoint](#httppost-queryendpoint)

<!-- tocstop -->

<!-- markdownlint-enable MD004 -->

## Authentication

When authentication is enabled for v1 API [`/info` call](server-rest.md#get-info), the
response contains authentication feature parameters, e.g.:

  ```json
  {
      "description": "",
      "creation_time": "0",
      "state_path": "e:\\dev\\TabPy\\tabpy-server\\tabpy_server",
      "server_version": "0.4.1",
      "name": "TabPy Server",
      "versions": {
          "v1": {
              "features": {
                  "authentication": {
                      "required": true,
                      "methods": {
                          "basic-auth": {}
                      }
                  }
              }
          }
      }
  }
  ```

v1 authentication specific features (see the example above):

<!-- markdownlint-disable MD013 -->

Property | Description
--- | ---
`required` | Authentication is never optional for a client to use if it is in the features list.
`methods` | List of supported authentication methods with their properties.
`methods.basic-auth` | TabPy requires basic access authentication. See [TabPy Server Configuration Instructions](server-config.md#authentication) for how to configure authentication.

<!-- markdownlint-enable MD013 -->

## http:get:: /status

Gets runtime status of deployed endpoints. If no endpoints are deployed in
the server, the returned data is an empty JSON object.

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

## http:get:: /endpoints

Gets a list of deployed endpoints and their static information. If no
endpoints are deployed in the server, the returned data is an empty JSON object.

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

## http:get:: /endpoints/:endpoint

Gets the description of a specific deployed endpoint. The endpoint must first
be deployed in the server (see the [TabPy Tools documentation](tabpy-tools.md)).

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

## http:post:: /evaluate

Executes a block of Python code, replacing named parameters with their provided
values.

The expected POST body is a JSON dictionary with two elements:

- A key `data` with a value that contains the parameter values passed to the
  code. These values are key-value pairs, following a specific convention for
  key names (`_arg1`, `_arg2`, etc.).
- A key `script` with a value that contains the Python code (one or more lines).
  Any references to the parameter names will be replaced by their values
  according to `data`.

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

It is possible to call a deployed function from within the code block through
the predefined function `tabpy.query`. This function works like the client
library's `query` method, and returns the corresponding data structure. The
function must first be deployed as an endpoint in the server (for more details
see the [TabPy Tools documentation](tabpy-tools.md)).

The following example calls the endpoint `clustering` as it was deployed in the
section [deploy-function](tabpy-tools.md#deploying-a-function):

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

The next example shows how to call `evaluate` from a terminal using curl. This
code queries the method `add` that was deployed in the section
[deploy-function](tabpy-tools.md#deploying-a-function):

```bash
curl -X POST http://localhost:9004/evaluate \
-d '{"data": {"_arg1":1, "_arg2":2},
     "script": "return tabpy.query(\"add\", x=_arg1, y=_arg2)[\"response\"]"}'
```

## http:post:: /query/:endpoint

Executes a function at the specified endpoint. The function must first be
deployed (see the [TabPy Tools documentation](tabpy-tools.md)).

This interface expects a JSON body with a `data` key, specifying the values
for the function, according to its original definition. In the example below,
the function `clustering` was defined with a signature of two parameters `x`
and `y`, expecting arrays of numbers.

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

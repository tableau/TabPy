# TabPy REST Interface

The server process exposes several REST APIs to get status and to execute
Python code and query deployed methods.

<!-- markdownlint-disable MD004 -->

<!-- toc -->

- [Authentication, /info and /evaluate](#authentication-info-and-evaluate)
- [http:get:: /status](#httpget-status)
- [http:get:: /endpoints](#httpget-endpoints)
- [http:get:: /endpoints/:endpoint](#httpget-endpointsendpoint)
- [http:post:: /query/:endpoint](#httppost-queryendpoint)

<!-- tocstop -->

<!-- markdownlint-enable MD004 -->

## Authentication, /info and /evaluate

Analytics Extensions API v1 is documented at
[https://tableau.github.io/analytics-extensions-api/docs/ae_api_ref.html](https://tableau.github.io/analytics-extensions-api/docs/ae_api_ref.html).

The following documentation is for methods not currently used by Tableau.

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

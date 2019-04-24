# TabPy REST Interface

The server process exposes several REST APIs to get status and to execute
Python code and query deployed methods.

<!-- markdownlint-disable MD004 -->

<!-- toc -->

- [GET /info](#get-info)
  * [URL](#url)
  * [Method](#method)
  * [URL parameters](#url-parameters)
  * [Data Parameters](#data-parameters)
  * [Response](#response)
- [API versions](#api-versions)

<!-- tocstop -->

<!-- markdownlint-enable MD004 -->

## GET /info

Get static information about the server. The method doesn't require any
authentication and returns supported API versions client can use together
with optional and required features.

### URL

```HTTP
/info
```

### Method

```HTTP
GET
```

### URL parameters

None.

### Data Parameters

None.

### Response

For successful call:

- Status: 200
- Content:

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

Response fields:

<!-- markdownlint-disable MD013 -->

Property | Description
--- | ---
`description` | String that is hardcoded in the `state.ini` file and can be edited there.
`creation_time` |  creation time in seconds since 1970-01-01, hardcoded in the `state.ini` file, where it can be edited.
`state_path` | state file path of the server (the value of the TABPY_STATE_PATH at the time the server was started).
`server_version` | TabPy Server version tag. Clients can use this information for compatibility checks.
`name` | TabPy server instance name. Can be edited in `state.ini` file.
`version` | Collection of API versions supported by the server. Each entry in the collection is an API version which has corresponding list of properties.
`version.`*`<ver>`* | Set of properties for an API version.
`version.`*`<ver>.features`* | Set of an API available features.
`version.`*`<ver>.features.<feature>`* | Set of a features properties. For specific details for property meaning of a feature check documentation for specific API version.
`version.`*`<ver>.features.<feature>.required`* | If true the feature is required to be used by client.

<!-- markdownlint-enable MD013 -->

For each API version there is set of properties, e.g. for v1 in the example
above features are:

See [TabPy Configuration](#tabpy-configuration) section for more information
on modifying the settings.

- **Examples**

Calling the method with curl:

```bash
curl -X GET http://localhost:9004/info
```

## API versions

TabPy supports the following API versions:

- v1 - see details at [api-v1.md](api-v1.md).

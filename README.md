# Bogi - REST over HTTP(S) testing tool

Bogi's goal is to allow testing HTTP(S) endpoints and services end-to-end.

Bogi generally follows JetBrains' [HTTP Request in Editor spec](https://github.com/JetBrains/http-request-in-editor-spec/blob/master/spec.md), which defines a nice and easy way to describe REST over HTTP actions and the expected return. Bogi might implement extensions to the spec to add functionality.

## Writing tests

Sample test validating that both requests return same response.
```
### Sample test
### Comment next to the request will be treated as a request ID
### request-to-v1
GET http://localhost:3000/api/v1/test

###
GET http://localhost:3000/api/v2/test

<> request-to-v1
```

## Running
Bogi accepts a required argument which should either be a path to directory
with `.http` files, or a single `.http` file.
```
./bogi.py requests/samples
```

Will run all `.http` files in `requests/samples` directory.
Process will exit with `0` exit code if all tests pass.

#### Not implemented
Request Handlers are currently ignored.  
#### Additions
Request Separators (`###`) next to the request definition are used to declare request ID.  
Request References (`<> name`) are used to reference other requests
sharing the same `.http` file by ID, instead of supplying response file path.

Bogi validates that referenced requests return the same response
(status code and response body) and returns error if they don't. 


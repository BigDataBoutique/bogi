# Bogi - REST over HTTP(S) testing tool

Bogi is a tool capable of executing scripted HTTP(S) requests and verifying the responses.

This can be used for several use-cases:
* Testing HTTP(S) endpoints and services end-to-end
* Running integration and system tests early on your CI/CD pipeline of choice
* Monitoring websites and APIs for uptime, latency and expected results

Bogi generally follows JetBrains' [HTTP Request in Editor spec](https://github.com/JetBrains/http-request-in-editor-spec/blob/master/spec.md), which defines a nice and easy way to describe REST over HTTP actions and the expected return. Bogi might implement extensions to the spec to add functionality.

## Writing HTTP tests

Sample test validating that both requests return same response.

```http
### Sample test
### Comment next to the request will be treated as a request ID
### request-to-v1
# @no-redirect
GET http://localhost:3000/api/v1/test

###
GET http://localhost:3000/api/v2/test

<> request-to-v1
```

## Running

Bogi accepts a required argument which should either be a path to directory with `.http` files, or a single `.http` file.

Executing:

```bash
./bogi.py ./examples
```

Will run all `.http` files in `examples` directory. These are mostly example files taken from or based on JetBrain's Request in Editor docs and examples.

The process will exit with `0` exit code if all tests pass, and a non-zero exit code otherwise.

## Running the dockerized version

```bash
docker run --rm -v `pwd`/examples:/usr/src/app/requests bigdataboutique/bogi
```

## Bogi's adaptation of RiE spec

### Added features

#### Easier check for returned status code

A dedicated syntax for easy HTTP status code checks, no request handler script required:

```
>STATUS 301
```

#### Request IDs and references

Request Separators (`###`) next to the request definition are used to declare request ID.

Request References (`<> name`) are used to reference other requests sharing the same `.http` file by ID, instead of supplying response file path.

Bogi validates that referenced requests return the same response (status code and response body) and returns error if they don't.

### Non-features

#### Javascript Request Handlers

Request Handlers are currently only partially implemented

#### Environment variables substitution not supported

The `{{foo}}` syntax for substitution with environment variables is not yet supported

#### Multi-part form-data POSTs

That isn't working either

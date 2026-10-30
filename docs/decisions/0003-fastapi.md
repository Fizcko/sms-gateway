# 0003. Move from Flask-RESTX to FastAPI

## Context

The Flask stack runs on Python 3.14, so moving was not forced. However, the project requires strict
typing with Pydantic, which Flask-RESTX does not offer, and Flask-BasicAuth has had no release since
2013.

## Decision

Rewrite the API with FastAPI and Pydantic, and replace Flask-JWT-Extended and Flask-BasicAuth with
PyJWT and a small module. Keep the URLs, the error format, the status codes and the environment
variables. Serve Swagger UI from local assets.

## Consequence

The whole API is type checked and documented from one set of models. Swagger 2.0 becomes OpenAPI 3,
and `/swagger.json` becomes `/openapi.json`. Authentication is now project code, covered by tests.

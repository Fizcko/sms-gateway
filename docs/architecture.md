# Architecture

`docs/` is written for coding agents working on this repository. The usage documentation (install,
routes, environment variables, upgrade) is in `Readme.md`.

## Overview

    client ── HTTP ──> FastAPI (uvicorn) ── SQL ──> MariaDB <── SQL ── gammu-smsd ── serial ──> modem
                           │                           ▲
                           └── python-gammu (inject) ──┘

Both processes run in one container. **The database is the only link between the API and SMSD**:
the API writes to the outbox and reads the tables, SMSD talks to the modem and fills them.

## Layout

| Path | Role |
|---|---|
| `pyproject.toml` | Dependencies, packaging, tool configuration |
| `src/sms_gateway/settings.py` | Typed configuration (`pydantic-settings`) |
| `src/sms_gateway/app.py` | `create_app`: wiring, docs, request logs |
| `src/sms_gateway/api/` | Routes, authentication, error format |
| `src/sms_gateway/schemas/` | Pydantic models of the API |
| `src/sms_gateway/services/` | Inbox reassembly, SMS injection, pagination |
| `src/sms_gateway/db/models.py` | ORM mapping of the Gammu tables |
| `src/sms_gateway/db/migrate.py`, `db/migrations/` | Alembic migrations |
| `entrypoint.sh` | Start sequence of the container |
| `scripts/check.sh` | Lint, type check and tests |

## Docker image

Stages: `base`, `gammu` (compiles Gammu), `dependencies` (compiles python-gammu against it),
`runtime`, then `test` or `final`.

- Gammu comes from the release tarball, whose SHA-256 is checked: Alpine ships 1.42.0.
- `gammu`, `gammu-smsd`, `libGammu` and `libgsmsd` come from one build, so they cannot diverge.
  To change version, follow *Upgrading Gammu* below.
- python-gammu is built with `--no-binary`. **Never install its wheel**: it has no SQL SMSD service,
  which only shows at runtime when sending.
- Swagger UI comes from the npm package `swagger-ui-dist`, with a checked SHA-512. It must support the
  OpenAPI version FastAPI generates: Swagger UI 4 cannot render OpenAPI 3.1.
- `gettext-dev` must stay out of the build: its `libintl.h` breaks linking against musl.

## Database

The schema is Gammu's v18, on InnoDB rather than Gammu's default MyISAM. The tests compare it to the
script in the sources of the Gammu actually built (R25).

| Revision | Effect |
|---|---|
| `0001` | Baseline: the v17 schema of the previous releases |
| `0002` | Gammu v18: `inbox` grouping columns, `outbox.SendDays` |
| `0003` | Every table moved to InnoDB |
| `0004` | Project table `webhook_state`, orphan `outbox_multipart` rows removed |

A database without `alembic_version` but with a `gammu` table is adopted: it is stamped according to
`gammu.Version` (17 or 18), then upgraded. MariaDB commits DDL immediately, so revision `0002` is
written to be replayed after an interruption.

To add a migration: new file in `db/migrations/versions/`, and update `db/models.py`.

### Upgrading Gammu

1. Update `GAMMU_VERSION` and `GAMMU_SHA256` in the `Dockerfile`, then run `scripts/check.sh`.
2. If `tests/integration/test_gammu_schema_parity.py` passes, the schema did not change.
3. Otherwise, read the schema history in Gammu's `docs/manual/smsd/tables.rst`, then add a revision
   after the latest one. Make each step safe to replay, and write the version in `gammu` last.
4. Update `db/models.py`, `GAMMU_SCHEMA_VERSION` and `_REVISION_OF_GAMMU_VERSION` (`db/migrate.py`).
5. Expose what users need in the API, and update `Readme.md` and the rules.

## API

Routes are grouped in `api/v1/`, one module per box, and registered in `app.py`. In each module,
`/all` is declared before `/{id}`. SMS routes receive their authentication from `create_app`, so a
route module never handles it. Swagger UI is served from local assets, because a gateway may have no
internet access.

Errors go through `api/errors.py`. Raise `ApiError`, which keeps the format stable. The status codes
and messages of authentication errors are kept from API v2, including the misspelled
`Basic authenfication fail`: it is part of the contract.

`/healthz` reads the modem state from the `phones` table, kept up to date by SMSD (R22 to R24). It
never talks to the modem: SMSD holds the serial port.

## Background thread

`services/background.py` runs next to the API, started by the `create_app` lifespan, only when the webhook
or the purge is configured. It holds the webhook deliveries and the daily purge.

The server must keep **one process**: several would deliver each message several times, and split the
login limit. `Inbox.Processed` is the delivery queue, and `webhook_state` is a project table: keep
project tables out of `GAMMU_TABLES` (`db/models.py`).

## Security

- No default secret in the image or the compose file: secrets come from `.env`, never committed.
- JWT: PyJWT, signed with `JWT_SECRET`, HMAC algorithms (`HS256`, `HS384`, `HS512`).
- Credentials are compared in constant time.
- `/v1/login` is limited per direct peer, in memory (R28).
- Webhook bodies are signed with HMAC-SHA256. The worker follows no redirect, and logs no URL or secret.
- `/etc/gammu-smsdrc` holds the database password and is readable by root only.

## Configuration

`settings.py` is the source of truth. A new variable goes there, and in the *Environment Variables*
section of `Readme.md`. If it has a default for the image, add it to the `Dockerfile`. If deployments
must set it, add it to `.env.example` and `docker-compose.yml`.

## Dependencies

`pyproject.toml` holds them, pinned: `[project.dependencies]` for runtime, `[dependency-groups]` for
development. The project is a package: new non-Python files must be declared in
`[tool.setuptools.package-data]`, or they will be missing from the image.

## Tests

Run `scripts/check.sh` before considering a task done. It builds the `test` stage and runs ruff, mypy
and pytest on Python 3.14 and Gammu 1.45.1, with a throwaway MariaDB. Arguments go to pytest. The host
has neither the right Python nor Gammu, so do not run the tools outside the image.

- `tests/unit`: no external service.
- `tests/integration`: real MariaDB. `test_gammu_end_to_end.py` adds the real `gammu-smsd` and
  python-gammu, with Gammu's dummy phone. No test uses a physical modem.

## Known limits

- Behind a reverse proxy, all clients share one login counter (R28).
- Login limits reset when the service restarts.
- Basic authentication has no attempt limit, only `/v1/login` has one.

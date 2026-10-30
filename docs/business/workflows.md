# Workflows

## Container start

1. The entrypoint writes the SMSD configuration (`GAMMU_SMSD_CONF`, readable by root only).
2. `python -m sms_gateway.db.migrate` creates the database if needed and applies the migrations.
   A failure stops the container.
3. `gammu-smsd` starts as a daemon.
4. The API starts.

A missing secret (see R17) stops the container at step 2, before SMSD and the API start.

## Sending a SMS

1. `POST /v1/send`: for each recipient, python-gammu encodes the text and injects it. The first
   part goes to `outbox`, the following ones to `outbox_multipart`. The answer gives the outbox ID:
   the SMS is queued, **not yet sent**.
2. SMSD picks up the outbox row, within its `SendBefore`, `SendAfter` and `SendDays` windows.
3. SMSD writes one `sentitems` row per part and removes the outbox rows.
4. Follow-up: `GET /v1/sentitems?destination=…`.

## Receiving a SMS

1. SMSD reads the modem and inserts each part into `inbox`, then sets its `MessageID`,
   `SequencePosition` and `PartCount` in a second statement.
2. Parts of a message delivered separately share the `MessageID` of the first one while they arrive
   within SMSD's `MultipartTimeout`.
3. `GET /v1/inbox` returns the reassembled message. While parts are missing, it has
   `Complete=false`; a later call shows the additional parts.

## Webhook delivery

1. On its first cycle, the background thread stores the highest `MessageID` in `webhook_state`.
2. Every 2 seconds, it looks for messages above this marker with an unprocessed part, oldest first.
3. A complete message is posted, then its parts are marked processed on a 2xx.
4. On a refusal, the cycle stops and resumes later, so the order is kept.
5. An incomplete message is skipped. Once older than `WEBHOOK_INCOMPLETE_DELAY`, it is logged and
   marked processed, unless a late part completes it first.

## Migrating a database

The upgrade procedure for operators is in `Readme.md`. On the code side:

1. `db/migrate.py` looks for `alembic_version`. If it is absent and a `gammu` table exists, it stamps
   the revision matching `gammu.Version`.
2. Alembic applies the remaining revisions: v18 columns, then InnoDB.
3. Any other Gammu version raises `UnsupportedSchemaError`, which stops the container.

# 0008. Webhook with the database as its queue

## Context

An application must react to received SMS without polling, and without losing messages while it is
down. Gammu's `RunOnReceive` runs a script, but SMSD waits for it, so a slow call delays reception, and
nothing retries a failed one. A WebSocket misses what arrives while disconnected.

## Decision

A background thread of the API reads the `inbox` table and posts signed messages. `Processed` records what
is done, so retries survive restarts. A `webhook_state` table records where the webhook started. Filtering
stays in the receiving application, and incomplete messages are not sent.

## Consequence

No message is lost and SMSD is never slowed down, at the cost of about 2 s of delay and at-least-once
delivery. A refused message blocks the following ones, to keep the order. A text whose part was lost never
reaches the application, which must read `/v1/inbox` if it needs it. The API must stay in a single process.

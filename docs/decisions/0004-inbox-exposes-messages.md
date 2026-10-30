# 0004. The inbox exposes reassembled messages

## Context

Schema v18 links received parts through `MessageID`. Exposing rows would make every client rebuild long
messages, but messages have no row of their own, and a part can be lost on the network.

## Decision

`/v1/inbox` returns one entry per message, identified by `MessageID`, and DELETE removes all its parts.
Incomplete messages are returned, flagged with `Complete=false`. Rules R1 to R8 of
`docs/business/rules.md` give the details.

## Consequence

Clients get whole messages and no SMS is hidden. This is a breaking change: lists have fewer entries,
and an ID kept for a later part no longer resolves. Older rows cannot be linked, so a long SMS received
before the upgrade stays split in several messages. Sent items keep their part-level behaviour for now,
which makes the two listings different.

# 0007. /healthz reports the phone

## Context

`/healthz` only checked the database, so a gateway unable to send could look healthy. The serial port
belongs to gammu-smsd, so the API cannot query the modem. The older `feature/phone_state` branch used
`SMSD.GetStatus()`, which reads the daemon's shared memory and returned the IMEI and IMSI on an open
route.

## Decision

Read the heartbeat gammu-smsd keeps in the `phones` table. A missing or expired row gives a 500, like
a database failure.

## Consequence

The check costs one SQL query and needs no access to the modem. A failure takes up to 70 s to show. A
modem failure makes the container `unhealthy`, without restarting it, unless an external tool does. A
slow modem start could do the same, hence a `start_period` of 90 s in the compose file.

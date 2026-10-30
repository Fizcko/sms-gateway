# 0002. Gammu schema v18 on InnoDB, migrated by Alembic

## Context

Gammu 1.45.1 refuses any database below schema v18. Tables were created by `create_all`, which cannot
change an existing table, on MyISAM, which has no transactions or reliable crash recovery. MyISAM also
hid a bug: the initial `gammu` row was never committed.

## Decision

Align the tables on v18 and move them to InnoDB. Manage the schema with Alembic, applied at start
before SMSD. Existing databases at v17 or v18 are detected and adopted.

## Consequence

Upgrades need no manual SQL, and the data is safer. The schema now differs from Gammu's script on the
storage engine only; the end-to-end tests check that SMSD works with it. The first start of the new
version changes the database in place, so a backup is needed. The next Gammu schema version will need
a new migration.

The tests read the reference schema from the sources of the Gammu built in the image, not from a copy,
so a Gammu upgrade that changes the schema fails the checks.

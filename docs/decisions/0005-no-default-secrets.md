# 0005. No default secrets

## Context

The image defaulted to `admin/admin`, a known JWT secret and a known database password. The compose file
and the README, both versioned, contained passwords.

## Decision

Remove these defaults. Read secrets from an uncommitted `.env`. The service refuses to start when a
secret needed by the security mode is missing.

## Consequence

A misconfiguration fails at start rather than running with public credentials. Existing deployments
must supply these variables when upgrading. The old passwords remain in the Git history and must be
treated as compromised.

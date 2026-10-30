# 0001. Build Gammu from source

## Context

The project needs Gammu 1.45.1. Alpine ships 1.42.0 on every branch, edge included. The python-gammu
wheels bundle Gammu statically but have no SQL SMSD service, so `InjectSMS` could not work with them,
and they target glibc only.

## Decision

Keep Alpine and compile Gammu from the release tarball, with a checked SHA-256, in a dedicated build
stage. Compile python-gammu from its source distribution against that build.

## Consequence

Gammu tools, libraries and bindings always share one version, and the final image stays around
170 MB. Builds take longer, especially under arm64 emulation,
and Gammu updates are now manual: nothing will bring security fixes in automatically.

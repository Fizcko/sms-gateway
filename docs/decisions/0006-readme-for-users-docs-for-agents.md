# 0006. README for users, docs/ for coding agents

## Context

Usage information was split between the README and `docs/`, so a user had to read internal material to
find the environment variables or the upgrade procedure.

## Decision

`Readme.md` is the usage documentation: install, routes, authentication, environment variables,
upgrade. `docs/` is for coding agents: architecture, business rules, workflows, glossary, decisions.
Dependencies move to `pyproject.toml`, and the project becomes an installable package.

## Consequence

A behaviour visible to users must be updated in both places: the rule in `docs/`, the usage in the
README. Installing the package in the image means a code change also reruns the dependency stage, which
slows local rebuilds.

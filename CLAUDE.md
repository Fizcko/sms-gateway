@docs/business/glossary.md

## 1. GENERAL BEHAVIOR
- Always answer in the language I prompt you in
- If something is ambiguous, ask your questions before coding. Do not assume.
- No dirty fix: look at the problem as a whole, or ask for more details
- Before considering a task done, run the tests, lint and typecheck of every
  part of the project you modified (front and/or back)
- End each task with a summary of the changes (3 bullet points max)

## 2. ABSOLUTE RULES

### Always
- Type strictly (TypeScript strict, Pydantic models)
- Write tests at the same time as the code
- Comment complex business logic functions

### Never
- Modify an existing test to make it pass without asking first
- Change a business rule without asking for confirmation first
- Commit or push without being asked

## 3. CODE

### Language
- Code is in English: names, comments, docstrings, messages in code
- Files in `docs/` stay in English

### Structure
- Separate responsibilities across modules; avoid large centralized files

### Testing
- Cover business behaviors, nominal cases, edge cases, expected errors
- Distinguish unit / integration tests where relevant
- One test per invariant: a failing test must identify a single rule

### When I ask for a fix
- Identify the root cause
- Fix without breaking existing tests
- Add a regression test

## 4. DOCUMENTATION
- Read `docs/business/rules.md` before any change to business logic
- When behavior changes, update `docs/` — **never the README.md**, which only
  covers the pitch, the prerequisites, the installation and the launch:
  - technical structure, data flow, sync, security, interface → `docs/architecture.md`
  - a business rule or an invariant → `docs/business/rules.md`
  - a process or a lifecycle → `docs/business/workflows.md`
  - a domain word or its name in the code → `docs/business/glossary.md`
- Add a file in `docs/decisions/` for any important decision, in the existing
  format: Context / Decision / Consequence, numbered after the last one
- Every new business rule must be covered by a test, referenced in the coverage
  table of `docs/business/rules.md` as `path/file::test_name` (never a file alone)


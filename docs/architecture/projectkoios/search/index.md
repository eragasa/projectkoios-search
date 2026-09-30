# `projectkoios.search` package implementation architecture

The package exposes independent search families through a small explicit
facade. The canonical authoring family is implemented by
[`evidence_retrieval`](evidence_retrieval/index.md).

## Module inventory

| Module | Role | Relationship to authoring retrieval |
|---|---|---|
| `evidence_retrieval` | Bounded text-only authoring evidence and deterministic lexical retrieval | Canonical new family |
| `literature` | Existing literature-review and SQLite prototype API | Independent legacy API; not wrapped or converted |
| `models` | Existing chunk and role-scoped records | Independent legacy API; not source evidence |
| `protocols` | Existing chunk and role-scoped protocols | Independent legacy API |
| `service` | Existing pass-through services | Independent legacy API |

Removing or adapting a legacy surface requires a later coordinated consumer
migration. The authoring family provides no compatibility aliases or adapters.

## Contents

- [`schematic.md`](schematic.md) — package relationships.
- [`implementation.md`](implementation.md) — facade and dependency rules.
- [`evidence_retrieval`](evidence_retrieval/index.md) — canonical authoring
  evidence implementation.

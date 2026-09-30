# `projectkoios.search` package implementation architecture

The package exposes independent search families and shared prototype boundaries
through a small explicit facade. The canonical authoring family remains
[`evidence_retrieval`](evidence_retrieval/index.md); existing APIs are documented
at their defining modules without aliases or conversion paths.

## Module inventory

| Module | Role | Relationship to authoring retrieval |
|---|---|---|
| [`evidence_retrieval`](evidence_retrieval/index.md) | Bounded text-only authoring evidence and deterministic lexical retrieval | Canonical independent family |
| [`literature`](literature/index.md) | Literature-review records, bundling, protocol, and SQLite FTS adapter | Independent prototype family |
| [`models`](models/index.md) | Chunk results, retrieval purposes, roles, admissions, requests, and results | Independent prototype records; not authoring source evidence |
| [`protocols`](protocols/index.md) | Unscoped and role-scoped index interfaces | Consumes `models` |
| [`service`](service/index.md) | Pass-through search services | Delegates through `protocols` |

Removing or adapting an existing surface requires a coordinated consumer
migration. The authoring family provides no compatibility aliases or adapters.

## Contents

- [`schematic.md`](schematic.md) — package and module relationships.
- [`implementation.md`](implementation.md) — facade, exports, and dependency rules.
- [`evidence_retrieval`](evidence_retrieval/index.md) — canonical authoring evidence implementation.
- [`literature`](literature/index.md) — reference-only literature retrieval prototype.
- [`models`](models/index.md) — shared prototype records and admission policy.
- [`protocols`](protocols/index.md) — structural index boundaries.
- [`service`](service/index.md) — pass-through service boundaries.

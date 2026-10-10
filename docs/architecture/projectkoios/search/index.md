# `projectkoios.search` package implementation architecture

The package exposes independent search families and shared prototype boundaries
through a small explicit facade. The canonical authoring family remains
[`evidence_retrieval`](evidence_retrieval/index.md); existing APIs are documented
at their defining modules without aliases or conversion paths.

## Module inventory

| Module | Role | Relationship to authoring retrieval |
|---|---|---|
| [`page_projection_chunking`](page_projection_chunking/index.md) | Pure deterministic block-local chunks from exact Ingestion page projection | Upstream source-chunk derivation only; no indexing or retrieval import |
| [`page_projection_lexical`](page_projection_lexical/index.md) | Backend-neutral structural chunk input, tokenizer, immutable lexical identities, and bounded request/results | Consumed by persistent lexical adapters; imports neither Ingestion nor concrete chunking |
| [`evidence_retrieval`](evidence_retrieval/index.md) | Bounded text-only authoring evidence and deterministic lexical retrieval | Canonical independent family |
| [`literature`](literature/index.md) | Literature-review records, bundling, protocol, and SQLite FTS adapter | Independent prototype family |
| [`models`](models/index.md) | Chunk results, retrieval purposes, roles, admissions, requests, and results | Independent prototype records; not authoring source evidence |
| [`protocols`](protocols/index.md) | Unscoped and role-scoped index interfaces | Consumes `models` |
| [`service`](service/index.md) | Pass-through search services | Delegates through `protocols` |

Removing or adapting an existing surface requires a coordinated consumer
migration. The authoring family provides no compatibility aliases or adapters.
The page-projection chunking leaf is imported directly rather than re-exported
by the package initializer, so importing indexing and retrieval modules does not
load Ingestion.

## Contents

- [`schematic.md`](schematic.md) — package and module relationships.
- [`implementation.md`](implementation.md) — facade, exports, and dependency rules.
- [`page_projection_chunking`](page_projection_chunking/index.md) — exact page-projection chunk derivation.
- [`page_projection_lexical`](page_projection_lexical/index.md) — backend-neutral lexical contracts and deterministic identities.
- [`evidence_retrieval`](evidence_retrieval/index.md) — canonical authoring evidence implementation.
- [`literature`](literature/index.md) — reference-only literature retrieval prototype.
- [`models`](models/index.md) — shared prototype records and admission policy.
- [`protocols`](protocols/index.md) — structural index boundaries.
- [`service`](service/index.md) — pass-through service boundaries.

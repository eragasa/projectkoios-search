# `projectkoios.search.page_search`

Search-owned SQLite FTS5 persistence and bounded BM25 retrieval for the
`solid-state-semiconductor-v1` page-search slice.

The build boundary accepts only exact Search-owned
`PageProjectionChunkingResult` objects assembled into a
`PageSearchBuildPlan`. It does not decode publication
JSON, inspect transcript paths, derive References authority, or expose source
locators. Pending catalog entries carry metadata but no projection.

## Public operations

- `PageSearchBuildDocument` binds catalog-safe citation metadata to one exact
  typed projection or a pending state.
- `PageSearchBuildPlan` validates the ordered immutable roster.
- `build_page_search_index(database=..., plan=...)` builds and atomically
  publishes a private derived database.
- `PageSearchIndex(database)` validates a fail-closed read-only index.
- `PageSearchIndex.status()` returns safe roster and coverage metadata.
- `PageSearchIndex.search(query, limit=10, offset=0)` returns bounded BM25
  results with filename, title, and physical-page citations.

The reader remains compatible with the deployed schema-1 generation while new
builds use schema 2 and retain each exact page-projection result identity
internally.

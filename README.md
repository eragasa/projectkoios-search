# projectkoios-search

Deterministic chunk derivation, full-text search, and semantic search
infrastructure for Project Koios.

Repository routing is documented in `projectkoios-bootstrap/maps/repositories.md`.

## Architecture

The Search-owned pure page-projection chunking boundary is documented in the
[`page_projection_chunking` implementation architecture](docs/architecture/projectkoios/search/page_projection_chunking/index.md).
Backend-neutral versioned lexical contracts are documented under
[`page_projection_lexical`](docs/architecture/projectkoios/search/page_projection_lexical/index.md),
and immutable MongoDB generations plus deterministic BM25 retrieval under
[`mongodb_page_projection_lexical`](docs/architecture/projectkoios/indexing/mongodb_page_projection_lexical/index.md).

## Contracts

The candidate-capable text-only authoring evidence foundation is documented in
the [`evidence_retrieval` implementation architecture](docs/architecture/projectkoios/search/evidence_retrieval/index.md).
Production manuscript admission and retrieval require the accepted References
authority boundary documented under
[`authority_bound_evidence`](docs/architecture/projectkoios/search/authority_bound_evidence/index.md).
These implementations do not accept the proposed contracts indexed in
[`docs/contracts/README.md`](docs/contracts/README.md).

## Solid-state semiconductor page search

The repository-owned [`page_search` operation](docs/architecture/projectkoios/search/page_search/index.md)
builds an atomic SQLite FTS5 index from exact Search-owned
`PageProjectionChunkingResult` objects and exposes a bounded read-only BM25 API. The
build plan carries catalog-safe document metadata and may retain explicit
pending roster entries; it does not decode publication JSON or read source
paths.

```bash
koios-page-search-index status \
  --database /explicit/path/to/search.sqlite3

koios-page-search-index query \
  --database /explicit/path/to/search.sqlite3 \
  --query "Fermi surface" \
  --limit 10
```

Only projected paragraphs, headings, and admitted figure captions enter FTS
text. Equation proposals and media locators remain outside the index.

API consumers import `PageSearchIndex` from `projectkoios.search`; they do not
open SQLite or depend on its schema.

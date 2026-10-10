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

The implemented text-only authoring evidence foundation is documented in the
[`evidence_retrieval` implementation architecture](docs/architecture/projectkoios/search/evidence_retrieval/index.md).
It does not accept the proposed contracts indexed in
[`docs/contracts/README.md`](docs/contracts/README.md).

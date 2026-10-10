# `projectkoios.search.page_projection_chunking`

This module owns the pure deterministic boundary from one exact Ingestion
`PageProjectionResult` to Search-owned block-local chunks. It is the only Search
module permitted to import that Ingestion leaf contract.

The fixed version-`1.0` policy emits one chunk for each projected paragraph,
heading, or figure-caption block. It does not join blocks, cross pages, invent
empty chunks, or perform indexing, retrieval, admission, persistence,
publication, model execution, workflow orchestration, or application
composition.

## Public classes

- [`PageProjectionChunkStyle`](PageProjectionChunkStyle/index.md)
- [`PageProjectionChunk`](PageProjectionChunk/index.md)
- [`PageProjectionChunkInventory`](PageProjectionChunkInventory/index.md)
- [`PageProjectionChunkingRequest`](PageProjectionChunkingRequest/index.md)
- [`PageProjectionChunkingResult`](PageProjectionChunkingResult/index.md)
- [`PageProjectionChunker`](PageProjectionChunker/index.md)

See the [schematic](schematic.md) and
[implementation](implementation.md) for dependency, identity, and fixture
details.

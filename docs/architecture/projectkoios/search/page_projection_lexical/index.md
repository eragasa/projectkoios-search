# `projectkoios.search.page_projection_lexical`

This backend-neutral module owns the structural input boundary from exact
Search `PageProjectionChunk` values into versioned lexical processing. It
defines deterministic Unicode tokenization, immutable corpus/index/generation
identities, bounded search requests, and generation-bound results. It imports no
Ingestion or database module and creates no alternate chunk DTO.

## Public classes

- [`PageProjectionLexicalChunk`](PageProjectionLexicalChunk/index.md)
- [`PageProjectionLexicalTokenizer`](PageProjectionLexicalTokenizer/index.md)
- [`PageProjectionLexicalIdentity`](PageProjectionLexicalIdentity/index.md)
- [`PageProjectionLexicalGeneration`](PageProjectionLexicalGeneration/index.md)
- [`PageProjectionLexicalSearchRequest`](PageProjectionLexicalSearchRequest/index.md)
- [`PageProjectionLexicalSearchHit`](PageProjectionLexicalSearchHit/index.md)
- [`PageProjectionLexicalSearchResult`](PageProjectionLexicalSearchResult/index.md)

See the [schematic](schematic.md) and
[implementation](implementation.md) for exact normalization, identity, bounds,
and dependency rules.

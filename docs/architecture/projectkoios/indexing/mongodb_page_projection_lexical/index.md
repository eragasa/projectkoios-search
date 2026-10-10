# `projectkoios.indexing.mongodb_page_projection_lexical`

This module owns MongoDB persistence and BM25 retrieval for exact structural
`PageProjectionLexicalChunk` inputs. An already-connected database capability
and an opaque storage-target ID are injected. The module contains no URI,
credential, endpoint, machine path, Ingestion import, concrete chunker import,
vector/model behavior, or application composition.

Immutable generation-scoped documents are staged idempotently, fully verified,
and exposed through one active-pointer compare-and-set. Retrieval selects that
one active generation and fails rather than truncates when its candidate bound
would be exceeded.

## Public classes

- [`MongoPageProjectionLexicalError`](MongoPageProjectionLexicalError/index.md)
- [`MongoPageProjectionLexicalProjector`](MongoPageProjectionLexicalProjector/index.md)
- [`MongoPageProjectionLexicalRetriever`](MongoPageProjectionLexicalRetriever/index.md)

See the [schematic](schematic.md) and
[implementation](implementation.md) for collection schemas, indexes, activation,
BM25, capability constraints, and development verification.

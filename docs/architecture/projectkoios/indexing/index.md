# `projectkoios.indexing` package implementation architecture

The package owns two facade-exported in-memory search indexes and one direct
MongoDB page-projection lexical adapter. Implementations consume contracts owned
by `projectkoios.search`; the facade itself contains no indexing behavior and
does not import the MongoDB leaf.

## Module inventory

- [`in_memory_chunk_index`](in_memory_chunk_index/index.md) — simple
  case-insensitive substring scoring over `TextChunk` records.
- [`in_memory_role_scoped_index`](in_memory_role_scoped_index/index.md) —
  purpose- and role-admitted deterministic BM25 retrieval.
- [`mongodb_page_projection_lexical`](mongodb_page_projection_lexical/index.md) —
  injected MongoDB immutable generations and bounded deterministic BM25.

## Contents

- [`schematic.md`](schematic.md) — facade and module relationships.
- [`implementation.md`](implementation.md) — exports and dependency direction.

# `projectkoios.indexing` package implementation architecture

The package facade exposes the repository's two in-memory search indexes. The
indexes consume records and request types owned by `projectkoios.search`; the
facade itself contains no indexing behavior.

## Module inventory

- [`in_memory_chunk_index`](in_memory_chunk_index/index.md) — simple
  case-insensitive substring scoring over `TextChunk` records.
- [`in_memory_role_scoped_index`](in_memory_role_scoped_index/index.md) —
  purpose- and role-admitted deterministic BM25 retrieval.

## Contents

- [`schematic.md`](schematic.md) — facade and module relationships.
- [`implementation.md`](implementation.md) — exports and dependency direction.

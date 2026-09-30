# `projectkoios.indexing.in_memory_role_scoped_index`

This module owns the in-memory BM25 implementation for role- and
purpose-scoped chunks. Its admission boundary is supplied by search-owned
models rather than inferred from query text.

## Public classes

- [`InMemoryRoleScopedChunkIndex`](InMemoryRoleScopedChunkIndex/index.md)

## Contents

- [`schematic.md`](schematic.md) — policy, record, request, and result flow.
- [`implementation.md`](implementation.md) — admission, BM25, and ordering.

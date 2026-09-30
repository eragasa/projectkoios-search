# `InMemoryChunkIndex`

`InMemoryChunkIndex` stores `TextChunk` objects in insertion order. `add_chunks`
appends an iterable without identity checks. `search(query, *, limit=10)` returns
positive-scoring `ChunkSearchResult` objects ordered by descending substring
match count, bounded by `limit`.

The class is process-local and mutable. It performs no persistence, source
validation, role admission, or deterministic identity construction.

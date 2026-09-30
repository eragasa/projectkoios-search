# `SearchService`

`SearchService` stores an injected `ChunkSearchIndex`. Its `search(query, *,
limit=10)` method forwards the same query and limit and returns the index's list
unchanged. It does not add purpose or corpus-role semantics.

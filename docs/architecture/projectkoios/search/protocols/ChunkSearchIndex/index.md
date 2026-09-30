# `ChunkSearchIndex`

**Kind:** structural `Protocol`.

The protocol defines `search(query: str, *, limit: int = 10) ->
list[ChunkSearchResult]`. It is the unscoped prototype boundary implemented by
`InMemoryChunkIndex` and consumed by `SearchService`.

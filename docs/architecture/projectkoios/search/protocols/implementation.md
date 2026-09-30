# `protocols` implementation

Both interfaces are `typing.Protocol` classes and rely on structural typing.
Neither is runtime-checkable and neither supplies default behavior.

```mermaid
flowchart LR
    ScopedService["RoleScopedSearchService"] --> ScopedProtocol["RoleScopedChunkSearchIndex.search(request)"]
    ScopedProtocol --> ScopedResults["tuple[RoleScopedChunkSearchResult, ...]"]
    SearchService["SearchService"] --> ChunkProtocol["ChunkSearchIndex.search(query, limit=10)"]
    ChunkProtocol --> ChunkResults["list[ChunkSearchResult]"]
```

The role-scoped protocol preserves the complete request object and immutable
tuple result boundary. The unscoped protocol accepts a query plus keyword-only
limit and returns a mutable list, matching the existing prototype API.

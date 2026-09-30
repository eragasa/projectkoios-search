# `projectkoios.indexing` package implementation

The initializer explicitly re-exports `InMemoryChunkIndex` and
`InMemoryRoleScopedChunkIndex`. Both implementations retain their indexed
records in process memory and perform no persistence or network I/O.

```mermaid
classDiagram
    class IndexingFacade["projectkoios.indexing"]
    class InMemoryChunkIndex
    class InMemoryRoleScopedChunkIndex
    class SearchModels["projectkoios.search.models"]

    IndexingFacade --> InMemoryChunkIndex : re-export
    IndexingFacade --> InMemoryRoleScopedChunkIndex : re-export
    InMemoryChunkIndex ..> SearchModels : results
    InMemoryRoleScopedChunkIndex ..> SearchModels : records and requests
```

The role-scoped index requires an explicit admission policy. The simpler chunk
index has no role or purpose boundary and remains a distinct prototype.

# `RoleScopedSearchService`

`RoleScopedSearchService` stores an injected `RoleScopedChunkSearchIndex` and
passes each `RoleScopedSearchRequest` directly to its `search` method. It
returns the tuple unchanged and adds no admission, ranking, or error handling.

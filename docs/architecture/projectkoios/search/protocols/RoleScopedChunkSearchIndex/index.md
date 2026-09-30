# `RoleScopedChunkSearchIndex`

**Kind:** structural `Protocol`.

The protocol defines `search(request: RoleScopedSearchRequest) ->
tuple[RoleScopedChunkSearchResult, ...]`. Passing the complete request preserves
purpose and exclusions across the service/index boundary.

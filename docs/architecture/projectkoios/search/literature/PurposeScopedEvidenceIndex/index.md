# `PurposeScopedEvidenceIndex`

**Kind:** structural `Protocol`.

The protocol defines `search(request: EvidenceSearchRequest) ->
tuple[EvidenceSearchResult, ...]`. It lets the bundle service depend on a
purpose-scoped retrieval boundary without selecting a storage implementation.

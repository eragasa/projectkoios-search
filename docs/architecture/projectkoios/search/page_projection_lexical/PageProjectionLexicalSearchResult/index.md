# `PageProjectionLexicalSearchResult`

`PageProjectionLexicalSearchResult` binds one exact request to one immutable
active generation, one retriever implementation ID, the versioned ordered
unique query terms, and an ordered tuple of hits. It enforces the request limit,
unique chunk IDs, contiguous ranks, descending score with ascending chunk-ID
ties, and query-order matched terms.

Its result ID binds request, generation, retriever, normalized terms, and hit
identities. Convenience properties expose exact generation, corpus, and index
IDs for provenance.

# `PageProjectionChunk`

`PageProjectionChunk` is one immutable Search-owned block-local chunk. It
preserves exact projected text and style, source-local page and block provenance,
all upstream result identities required to resolve the input, a content digest,
fixed processor identity/version, and a deterministic source-local chunk
identity. Global result/provider
bindings remain resolvable fields but do not renumber otherwise identical local
evidence. It carries no global ordinal, corpus role,
retrieval admission, rank, score, or publication state.

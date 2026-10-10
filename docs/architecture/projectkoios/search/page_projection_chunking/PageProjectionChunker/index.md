# `PageProjectionChunker`

`PageProjectionChunker` directly specializes
`DataObjectActionizer[PageProjectionChunkingRequest,
PageProjectionChunkingResult]`. Its keyword-only `action` method performs the
fixed synchronous side-effect-free block-local derivation. It does not index,
retrieve, admit, persist, publish, invoke models, orchestrate workflow, or
compose applications.

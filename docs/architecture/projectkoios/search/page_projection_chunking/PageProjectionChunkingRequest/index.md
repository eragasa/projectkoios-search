# `PageProjectionChunkingRequest`

`PageProjectionChunkingRequest` directly specializes
`DataObjectActionRequest`. It accepts one exact fresh current-schema-valid
`PageProjectionResult` and exposes no policy knobs. Its identity binds the
upstream result plus fixed block-local policy and contract versions. Construction
and action-time freshness and identity validation reject stale or altered input.

# `MongoPageProjectionLexicalProjector`

`MongoPageProjectionLexicalProjector` consumes exact structural lexical chunks
and builds immutable Mongo generation documents. It creates and verifies exact
unique indexes, derives input-order-independent corpus/index/generation
identities, performs idempotent `$setOnInsert` staging, rereads and hashes the
complete generation, and transitions verified metadata to `ready`.

`active_snapshot` returns one coherent generation-and-revision observation.
`activate` repeats verification and changes only the singleton active pointer
through compare-and-set against the caller's exact observed generation and
revision. `rebuild` composes stage and revision-bound activation. The projector never deletes,
drops, renames, starts a transaction, constructs a client, or imports Ingestion.

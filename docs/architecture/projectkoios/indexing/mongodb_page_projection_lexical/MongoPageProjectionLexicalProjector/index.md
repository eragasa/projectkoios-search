# `MongoPageProjectionLexicalProjector`

`MongoPageProjectionLexicalProjector` consumes exact structural lexical chunks
and builds immutable Mongo generation documents. It creates and verifies exact
unique indexes, derives input-order-independent corpus/index/generation
identities, performs idempotent `$setOnInsert` staging, rereads and hashes the
complete generation, and transitions verified metadata to `ready`.

`activate` repeats verification and changes only the singleton active pointer
through compare-and-set against the caller's expected generation and stored
revision. `rebuild` composes stage and activation. The projector never deletes,
drops, renames, starts a transaction, constructs a client, or imports Ingestion.

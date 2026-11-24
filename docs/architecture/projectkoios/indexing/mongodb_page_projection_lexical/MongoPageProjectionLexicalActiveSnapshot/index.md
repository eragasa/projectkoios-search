# `MongoPageProjectionLexicalActiveSnapshot`

`MongoPageProjectionLexicalActiveSnapshot` is the immutable Mongo-specific
observation used to bind one active lexical generation to the exact singleton
pointer revision read with it. Both values are absent together before first
activation; a present generation always has a positive revision.

The snapshot lets an operator retain explicit absent state or a complete
`(generation_id, revision)` pair and require both during later activation. This
prevents an A→B→A pointer sequence from satisfying a stale generation-only
expectation.

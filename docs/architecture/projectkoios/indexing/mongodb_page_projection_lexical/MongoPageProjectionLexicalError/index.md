# `MongoPageProjectionLexicalError`

`MongoPageProjectionLexicalError` reports fail-closed persistent projection,
verification, activation, or retrieval failure. It is the adapter-level runtime
error; callers must not interpret failure as an empty successful result or a
partially active generation.

The development verifier maps errors to fixed redacted categories and never
prints exception text, connection material, endpoint details, or credentials.

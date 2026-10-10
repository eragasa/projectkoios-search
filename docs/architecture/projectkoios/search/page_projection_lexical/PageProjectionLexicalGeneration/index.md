# `PageProjectionLexicalGeneration`

`PageProjectionLexicalGeneration` is an immutable value identifying one exact
lexical build. It binds corpus, index, schema, tokenizer, and projector IDs; the
canonical chunk-manifest and full index-manifest SHA-256 values; and chunk,
posting, term, and total-document-length measures.

Construction validates exact identities, lowercase 64-character digests, and
bounded nonnegative built-in integer counts, then derives `generation_id` from
all fields. Activation state and storage location are deliberately not part of
this backend-neutral semantic value.

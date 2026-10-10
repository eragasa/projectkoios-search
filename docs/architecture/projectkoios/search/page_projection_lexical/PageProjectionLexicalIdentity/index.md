# `PageProjectionLexicalIdentity`

`PageProjectionLexicalIdentity` derives backend-neutral lexical identities. A
chunk manifest validates unique exact chunk IDs and sorts them. The corpus ID
binds that complete canonical inventory. The index ID binds corpus, tokenizer,
persistent schema, and hexadecimal BM25 `k1`/`b` values.

All derivations use sorted compact UTF-8 JSON and SHA-256. Input order therefore
does not change corpus or index identity, while any bound semantic change does.

# `PageProjectionLexicalSearchRequest`

`PageProjectionLexicalSearchRequest` is a frozen bounded query value. It accepts
an exact nonblank valid-UTF-8 query of at most 2,000 characters and 256 unique
versioned lexical terms, a result limit in `[1, 100]`, and a candidate-posting
ceiling in `[1, 100000]`.

Its derived `request_id` binds the exact query and both applied bounds. It has no
caller-selected tokenizer, BM25 parameter, generation, role, model, vector, or
backend switch.

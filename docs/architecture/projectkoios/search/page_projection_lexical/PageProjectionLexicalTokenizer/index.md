# `PageProjectionLexicalTokenizer`

`PageProjectionLexicalTokenizer` applies version-`1.0` Unicode casefolding and
the fixed Unicode-aware term grammar. `tokens` preserves source order and
repetitions; `query_terms` deduplicates in first-seen order. Input is exact,
nonblank, strict UTF-8, and bounded to 262,144 bytes.

Its tokenizer ID is the exact authoritative opaque value
`projectkoios.search.page-projection-lexical-tokenizer:1.0`; it is never
substituted by a derived configuration hash. Version `1.0` governs the exact
regular expression and case-normalization rule. The tokenizer performs no
stemming, stop-word removal, locale selection, persistence, or model execution.

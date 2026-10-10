# `PageProjectionLexicalSearchHit`

`PageProjectionLexicalSearchHit` retains one exact chunk ID, positive finite
BM25 score, contiguous one-based rank, and unique matched query terms. Its
derived `hit_id` binds those fields and the score's exact hexadecimal
floating-point representation.

The hit does not copy chunk text or lineage and grants no citation-resolution or
publication authority; consumers resolve the stable chunk ID against the same
generation.

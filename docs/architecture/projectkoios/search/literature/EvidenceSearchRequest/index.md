# `EvidenceSearchRequest`

`EvidenceSearchRequest` is a frozen query record carrying text, a
`RetrievalPurpose`, an `EvidenceCorpusRole`, and a result limit. Construction
requires query text with a nonblank trimmed interpretation and at most 2,000
characters, plus a non-boolean limit in the inclusive range 1–100.

Purpose and corpus restrictions are enforced by the receiving index as well as
by callers such as `LiteratureEvidenceBundleService`.

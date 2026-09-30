# `DeterministicLexicalEvidenceRetriever`

**Base:** `DataObjectActionizer[EvidenceRetrievalRequest, EvidenceRetrievalResult]`.

This semantic performer binds one immutable `EvidenceCorpus` and performs
deterministic BM25 retrieval. Callers cannot provide a separate corpus ID or
item tuple. Its `action(*, request)` method delegates directly to
`retrieve(*, request)`, which returns `EvidenceRetrievalResult`; no duplicate
operation path exists.

The retriever derives `index_id` from the corpus's derived `corpus_id`, its
canonical ordered `evidence_item_id` manifest, token pattern, BM25 parameters,
and `IMPLEMENTATION_IDENTITY`. It orders scored candidates by descending score
then stable evidence item ID, applies strongest-first bounded selection and a
per-bibliographic-work cap, and records omissions. It performs no I/O and does
not catch unexpected defects as insufficiency.

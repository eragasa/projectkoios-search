# `EvidenceRetrievalResult`

**Base:** `DataObjectActionResult`.

The frozen, slotted, keyword-only result binds one exact
`EvidenceRetrievalRequest` to:

- retriever implementation, corpus, and index IDs;
- normalized lexical terms and one closed outcome;
- ordered `RankedEvidenceItem` records;
- candidate and exclusive omission counts;
- missing required bibliographic work IDs; and
- bounded warning codes.

The deterministic init-false `result_id` is assigned by `identity_for` and
binds the request ID, retriever/index evidence, outcome, selected ranked IDs,
omissions, and warnings. Evidence is present exactly for
`EVIDENCE_AVAILABLE`.

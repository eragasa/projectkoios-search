# `EvidenceCorpusCompositionResult`

**Base:** `DataObjectActionResult`.

This frozen, slotted, keyword-only result binds one exact
`EvidenceCorpusCompositionRequest`, the composer implementation identity, and
the derived `EvidenceCorpus`. Construction rejects a corpus whose role or
canonical items differ from the request.

The init-false `result_id` binds the request ID, composer implementation
identity, and derived corpus ID.

# `EvidenceCorpus`

**Base:** `DataObjectModel`.

`EvidenceCorpus` is the frozen, slotted, keyword-only owner of one admitted
authoring corpus. It accepts only `REFERENCE_EVIDENCE`, requires an immutable
tuple of exact `EvidenceItem` values with matching roles, rejects duplicate
`evidence_item_id` values, and stores items in ascending identity order.

The init-false `corpus_id` is derived from the admitted role and canonically
ordered evidence item IDs. Callers therefore cannot provide or override corpus
identity.

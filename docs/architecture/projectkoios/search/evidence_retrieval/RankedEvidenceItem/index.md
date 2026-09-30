# `RankedEvidenceItem`

**Base:** `DataObjectModel`.

This frozen, slotted, keyword-only record binds one `EvidenceItem` to its
positive finite BM25 score, contiguous selected rank, ordered matched query
terms, and tie key. The tie key must equal `evidence_item_id`.

The deterministic init-false `ranked_evidence_item_id` is assigned by
`identity_for`. It binds the evidence item ID, exact hexadecimal float score,
rank, matched terms, and tie key.

# `EvidenceItem`

**Base:** `DataObjectModel`.

`EvidenceItem` is one frozen, slotted, keyword-only text item from an admitted
independent reference. It carries:

- `bibliographic_work_id` and projected `ReferenceIdentityStatus`;
- optional accepted canonical citekey;
- `source_asset_id`, `transcript_id`, `page_id`, `block_id`, and ordered
  `source_span_ids`;
- indexed and retained text with matching SHA-256 digests; and
- bounded `EvidenceWarning` records.

Only `AuthoringCorpusRole.REFERENCE_EVIDENCE` is valid. The init-false
`evidence_item_id` is assigned through class-owned `identity_for` behavior and
binds all represented values, including warning IDs. Indexed text is useful for
retrieval; retained text remains the inspection and quotation basis.

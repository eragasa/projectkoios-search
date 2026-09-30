# `EvidenceCorpusCompositionRequest`

**Base:** `DataObjectActionRequest`.

This frozen, slotted, keyword-only request carries the admitted authoring role
and exact evidence items to compose. It applies the same role, tuple, type, and
uniqueness checks as `EvidenceCorpus` and canonicalizes items by
`evidence_item_id`.

The init-false `request_id` binds the request type, admitted role, and canonical
item identity manifest. Equivalent input order therefore represents the same
composition intent.

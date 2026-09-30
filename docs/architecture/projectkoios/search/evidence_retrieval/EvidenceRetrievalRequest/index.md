# `EvidenceRetrievalRequest`

**Base:** `DataObjectActionRequest`.

The frozen, slotted, keyword-only request represents complete immutable lexical
retrieval intent:

- `MANUSCRIPT_AUTHORING` purpose;
- bounded query representation;
- opaque `target_id`, never target bytes;
- bounded optional and required bibliographic work IDs; and
- result, per-work, and aggregate-text limits within fixed hard maxima.

The deterministic init-false `request_id` is assigned by `identity_for` and
binds every intent field and applied bound. Live stores, clients, target text,
and execution state are absent.

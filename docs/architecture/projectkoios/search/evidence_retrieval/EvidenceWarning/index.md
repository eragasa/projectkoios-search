# `EvidenceWarning`

**Base:** `DataObjectModel`.

`EvidenceWarning` is a frozen, slotted, keyword-only record containing a bounded
machine-readable `code`, bounded `detail`, and deterministic init-false
`warning_id`.

`identity_for(*, code, detail)` binds the exact warning type and content. The
item retaining the warning already binds page and block IDs, so the warning
remains block-resolvable without duplicating locators.

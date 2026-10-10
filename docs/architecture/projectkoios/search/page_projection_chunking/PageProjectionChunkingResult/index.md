# `PageProjectionChunkingResult`

`PageProjectionChunkingResult` directly specializes `DataObjectActionResult`.
It binds the exact request, complete deterministic chunk inventory, and fixed
chunker implementation identity/version. Construction independently re-derives
the inventory and rejects omission, alteration, reordering, or unsupported
implementation provenance.

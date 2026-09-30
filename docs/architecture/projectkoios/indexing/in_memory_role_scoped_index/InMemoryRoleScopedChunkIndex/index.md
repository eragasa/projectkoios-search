# `InMemoryRoleScopedChunkIndex`

`InMemoryRoleScopedChunkIndex` is a mutable, process-local deterministic BM25
index for `RoleScopedChunk` records. Construction requires an explicit
`RoleAdmissionPolicy`; records are admitted only when their corpus role is
allowed by that policy and the request purpose appears in the record's own
`admitted_purposes`.

Search also honors excluded record IDs, drops zero-score records, orders by
score descending then `record_id`, applies the request limit, and assigns
contiguous one-based ranks. The class performs no persistence or fallback to an
unapproved purpose or corpus role.

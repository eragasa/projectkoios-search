# `RoleScopedChunk`

`RoleScopedChunk` is a frozen record containing a nonempty `record_id`, shared
`TextChunk`, explicit `CorpusRole`, and unique tuple of explicit
`RetrievalPurpose` admissions. The record-level purpose list is checked
separately from policy-level role admission by the role-scoped index.

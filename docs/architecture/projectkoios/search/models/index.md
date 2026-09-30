# `projectkoios.search.models`

This module owns the existing unscoped chunk result and the role/purpose-scoped
records used by search protocols, services, and indexing implementations.
These records are prototypes, not the accepted source-linked evidence contract.
The proposal's normative
[retrieval-purpose and admission rules](../../../../contracts/retrieval-evidence.md#retrieval-purpose-and-admission)
provide contract context without changing the implementation status.

## Public classes

- [`ChunkSearchResult`](ChunkSearchResult/index.md)
- [`UnsupportedRetrievalPurposeError`](UnsupportedRetrievalPurposeError/index.md)
- [`RetrievalPurpose`](RetrievalPurpose/index.md)
- [`CorpusRole`](CorpusRole/index.md)
- [`PurposeAdmission`](PurposeAdmission/index.md)
- [`RoleAdmissionPolicy`](RoleAdmissionPolicy/index.md)
- [`RoleScopedChunk`](RoleScopedChunk/index.md)
- [`RoleScopedSearchRequest`](RoleScopedSearchRequest/index.md)
- [`RoleScopedChunkSearchResult`](RoleScopedChunkSearchResult/index.md)

## Contents

- [`schematic.md`](schematic.md) — model and admission relationships.
- [`implementation.md`](implementation.md) — validation and fixed course policy.

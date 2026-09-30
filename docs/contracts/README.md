# Search contracts

This directory indexes owner-local contract proposals maintained by
`projectkoios-search`. Neither listed proposal has an accepted baseline. The
implemented authoring family has separate
[Search-owned implementation architecture](../architecture/projectkoios/search/evidence_retrieval/index.md);
that implementation does not accept these broader proposals.

| Contract ID | Proposal document | Scope |
|---|---|---|
| `projectkoios.search.evidence-unit` | [`retrieval-evidence.md`](retrieval-evidence.md#contract-metadata-evidence-unit) | Source-linked evidence units and identity |
| `projectkoios.search.evidence-bundle` | [`retrieval-evidence.md`](retrieval-evidence.md#contract-metadata-evidence-bundle) | Retrieval observations, fusion evidence, and bounded bundles |

Cross-repository discovery is provided by the
[Project Koios contract catalog](https://github.com/eragasa/projectkoios/blob/main/docs/contracts/README.md).
Lifecycle, pre-release versioning, compatibility, and conformance follow the
[Project Koios contract governance policy](https://github.com/eragasa/projectkoios/blob/main/docs/policies/contracts.md).
Task and recovery authority rules are defined by the
[Project Koios task and recovery policy](https://github.com/eragasa/projectkoios/blob/main/docs/policies/task-and-recovery-records.md).

The commit-pinned Project Koios
[evidence-grounded long-form authoring architecture](https://github.com/eragasa/projectkoios/blob/d8a4867d581af81b76d10685b295df2abd1d632e/docs/architecture/v0/index.md#evidence-grounded-long-form-authoring)
governs the bounded prototype direction. Deleted decision records are not
architecture authority for these proposals.

Each proposal document records its own status and target version. This index
does not authorize implementation, indexing, embedding generation, fusion,
API integration, answer generation, or contract acceptance.

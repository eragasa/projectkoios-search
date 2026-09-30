# `projectkoios.search.evidence_retrieval`

**Status:** implemented prototype; not an accepted contract.

This module owns the bounded text-only evidence family for the first
`manuscript_authoring` lexical slice. It contains immutable source-linked
records and one semantic performer. Its implementation does not accept the
broader [proposed retrieval contracts](../../../../contracts/README.md).
It does not contain target bytes,
generated/course/manuscript evidence, rights decisions, persistence, vectors,
equation types, API behavior, generation, serialization schemas, or workflow.

The Project Koios
[evidence-grounded long-form authoring boundary](https://github.com/eragasa/projectkoios/blob/d8a4867d581af81b76d10685b295df2abd1d632e/docs/architecture/v0/index.md#evidence-grounded-long-form-authoring)
is product-boundary authority. This page and its children are the Search-owned
implementation architecture.

## Public classes

- [`AuthoringCorpusRole`](AuthoringCorpusRole/index.md)
- [`AuthoringPurpose`](AuthoringPurpose/index.md)
- [`DeterministicLexicalEvidenceRetriever`](DeterministicLexicalEvidenceRetriever/index.md)
- [`EvidenceItem`](EvidenceItem/index.md)
- [`EvidenceRetrievalOutcome`](EvidenceRetrievalOutcome/index.md)
- [`EvidenceRetrievalRequest`](EvidenceRetrievalRequest/index.md)
- [`EvidenceRetrievalResult`](EvidenceRetrievalResult/index.md)
- [`EvidenceWarning`](EvidenceWarning/index.md)
- [`RankedEvidenceItem`](RankedEvidenceItem/index.md)
- [`ReferenceIdentityStatus`](ReferenceIdentityStatus/index.md)

## Contents

- [`schematic.md`](schematic.md) — class and action relationships.
- [`implementation.md`](implementation.md) — identities, bounds, BM25, and
  deterministic selection.

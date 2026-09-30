# `projectkoios.search.literature`

This module owns the existing literature-review evidence records, bundle
service, index protocol, and read-only SQLite FTS5 adapter. It is independent
of [`evidence_retrieval`](../evidence_retrieval/index.md) and uses the legacy
`RetrievalPurpose.LITERATURE_REVIEW` boundary.

The implementation facts formerly summarized only in the extracted candidate
[literature evidence document](../../../../contracts/literature-evidence-retrieval.md)
are represented by this source-mirrored architecture. Broader proposed evidence
requirements remain in the normative sections of the
[source-linked retrieval evidence contract](../../../../contracts/retrieval-evidence.md#normative-scope-and-conformance);
this module does not thereby accept that proposal.

## Public classes

- [`EvidenceCorpusRole`](EvidenceCorpusRole/index.md)
- [`EvidencePassage`](EvidencePassage/index.md)
- [`EvidenceSearchResult`](EvidenceSearchResult/index.md)
- [`EvidenceSearchRequest`](EvidenceSearchRequest/index.md)
- [`PurposeScopedEvidenceIndex`](PurposeScopedEvidenceIndex/index.md)
- [`LiteratureClaimQuery`](LiteratureClaimQuery/index.md)
- [`LiteratureEvidenceItem`](LiteratureEvidenceItem/index.md)
- [`LiteratureEvidenceBundle`](LiteratureEvidenceBundle/index.md)
- [`LiteratureEvidenceBundleService`](LiteratureEvidenceBundleService/index.md)
- [`SqliteFtsReferenceEvidenceIndex`](SqliteFtsReferenceEvidenceIndex/index.md)

## Contents

- [`schematic.md`](schematic.md) — literature retrieval relationships.
- [`implementation.md`](implementation.md) — validation, selection, and SQLite behavior.

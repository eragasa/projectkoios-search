# Authoring evidence foundation

Status: implemented prototype; not an accepted contract.

This text-only foundation implements the Search-owned boundary in the
commit-pinned Project Koios
[evidence-grounded long-form authoring architecture](https://github.com/eragasa/projectkoios/blob/ef06808d03b45df9d802ec16de24441e1bcbb8da/docs/architecture/v0/index.md#evidence-grounded-long-form-authoring).
It does not authorize source use, accept the proposed retrieval contracts, or
make scientific, rights, editorial, or publication decisions.

## Boundary

`EvidenceItem` retains an independent reference's bibliographic status, source
asset, transcript, page, block, ordered source spans, indexed text, retained
text, digests, and bounded warning details. Its stable identity is derived from
those values. Only the `reference_evidence` corpus role is representable.
Candidate references cannot carry an accepted citekey.

`EvidenceQuery` supports only `manuscript_authoring`. It receives a bounded
query representation and opaque target identity, never target bytes. Optional
work filters and required works are bounded. Existing manuscript or course
text, generated prose, model answers, and solution material are not evidence
items and have no compatibility conversion into this family.

`DeterministicLexicalEvidenceRetriever` directly implements
`DataObjectActionizer[EvidenceQuery, EvidenceBundle]`. `action` delegates to the
single `retrieve` implementation. It uses deterministic BM25, orders by score
then stable evidence-item identity, retains the strongest eligible item, and
fills remaining positions under a per-work cap. The result records ranks,
matched terms, tie keys, warnings, missing required works, and omissions caused
by result, per-work, aggregate-text, or required-work rules.

The closed outcomes are:

- `EVIDENCE_AVAILABLE`;
- `INSUFFICIENT_EVIDENCE`;
- `INVALID_REQUEST`; and
- `INFRASTRUCTURE_FAILURE`.

Insufficiency is mechanical. It is not a claim that evidence is scientifically
irrelevant or fails to support an author's claim. The in-memory retriever has no
external infrastructure dependency and does not catch unexpected defects as
insufficiency; the result family keeps infrastructure failure distinct for a
caller that has such evidence.

## Fixed hard bounds

| Value | Maximum |
|---|---:|
| Query characters | 2,000 |
| Normalized query terms | 256 |
| Opaque identity characters | 512 |
| Work filters or required works | 32 each |
| Results | 50 |
| Results per bibliographic work | 10 |
| Indexed text per item | 20,000 characters |
| Retained text per item | 40,000 characters |
| Ordered source spans per item | 32 |
| Warning details per item | 32 |
| Warning code | 128 characters |
| Warning detail | 1,000 characters |
| Aggregate selected text | 100,000 characters |

A request may choose lower result, per-work, and aggregate-text limits. Values
outside the hard bounds fail before retrieval.

## Compatibility

The existing chunk, role-scoped, and literature retrieval APIs remain intact
for their current consumers. The authoring family neither wraps nor silently
converts them. Removing those prototypes requires a later coordinated consumer
migration.

This slice adds no vectors, equation evidence, SQLite or other persistence,
API, generation, workflow, serialization schema, format version, or migration.

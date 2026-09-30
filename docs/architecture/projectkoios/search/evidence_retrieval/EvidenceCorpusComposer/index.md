# `EvidenceCorpusComposer`

**Base:** `DataObjectActionizer[EvidenceCorpusCompositionRequest, EvidenceCorpusCompositionResult]`.

This stateless semantic performer constructs an `EvidenceCorpus` from the
request's admitted role and canonical items, then returns a bound composition
result. `action(*, request)` delegates directly to `compose(*, request)`, so
there is one composition implementation path.

The composer performs no I/O, persistence, serialization, or evidence
transformation.

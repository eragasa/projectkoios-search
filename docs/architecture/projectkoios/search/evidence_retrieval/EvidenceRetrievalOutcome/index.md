# `EvidenceRetrievalOutcome`

**Kind:** closed `StrEnum`.

The outcomes are:

- `EVIDENCE_AVAILABLE` — one or more bounded items were selected;
- `INSUFFICIENT_EVIDENCE` — a valid completed search mechanically selected no
  item or could not retain a required work;
- `INVALID_REQUEST` — the bounded lexical request is unsupported; and
- `INFRASTRUCTURE_FAILURE` — retrieval could not complete.

Insufficiency is not a relevance, entailment, truth, or scientific-support
judgment.

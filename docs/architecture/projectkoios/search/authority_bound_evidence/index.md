# Authority-bound evidence

`projectkoios.search.authority_bound_evidence` is the Search-owned production
admission boundary for manuscript-authoring evidence. It composes three exact,
public inputs:

- **A:** Search `PageProjectionChunkingResult`;
- **B:** Ingestion `PageProjectionEvidenceEnrichmentResult`;
- **C:** References `SearchReferenceAuthorityProjection` at an explicitly
  expected current result ID.

It admits an `EvidenceItem` only when A, B, and C are complete and mutually
consistent. Every other chunk receives an explicit omission. Existing candidate-
capable evidence types and the raw-corpus lexical retriever remain prototype and
review interfaces; production callers use the authority-bound retriever, which
cannot be constructed from a raw `EvidenceCorpus`.

The module imports only the public Ingestion enrichment leaf and the public
References course-authority module. It does not traverse Ingestion-owned reading
or transcript graphs, and it does not synthesize bibliography, citekeys, assets,
or producer warnings.

# Authority-bound evidence

`projectkoios.search.authority_bound_evidence` is the Search-owned production
admission boundary for manuscript-authoring evidence. It composes three exact,
public inputs:

- **A:** Search `PageProjectionChunkingResult`;
- **B:** Ingestion `PageProjectionEvidenceEnrichmentResult`;
- **C:** References
  `projectkoios.references.courses.authority.search_projection.SearchReferenceAuthorityProjection`
  at an explicitly expected current result ID, produced by the References-owned
  typed request/actionizer/result boundary.

It admits an `EvidenceItem` only when A, B, and C are complete and mutually
consistent. Every other chunk receives an explicit omission. Existing candidate-
capable evidence types and the raw-corpus lexical retriever remain prototype and
review interfaces. Production callers construct an immutable authority retrieval
request from the admission result and bounded lexical intent; the stateless
authority-bound Actionizer never accepts a raw `EvidenceCorpus`.

The module imports only the public Ingestion enrichment leaf and the exact
References defining leaves `courses.authority.evidence` and
`courses.authority.search_projection`. It does not traverse Ingestion-owned reading
or transcript graphs, and it does not synthesize bibliography, citekeys, assets,
or producer warnings.

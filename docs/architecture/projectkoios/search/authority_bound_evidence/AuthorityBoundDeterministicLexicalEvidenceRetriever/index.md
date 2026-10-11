# AuthorityBoundDeterministicLexicalEvidenceRetriever

`AuthorityBoundDeterministicLexicalEvidenceRetriever` is the production
manuscript-authoring retrieval entry point. Its constructor accepts only an
exact, replay-current `AuthorityBoundEvidenceAdmissionResult`, never a raw or
candidate-capable `EvidenceCorpus`, and delegates lexical ranking only after
admission validation.

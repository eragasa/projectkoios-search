# AuthorityBoundDeterministicLexicalEvidenceRetriever

`AuthorityBoundDeterministicLexicalEvidenceRetriever` is the stateless
production manuscript-authoring retrieval Actionizer. Its sole `action` accepts
an exact, replay-current `AuthorityBoundEvidenceRetrievalRequest`, never a raw
or candidate-capable `EvidenceCorpus`, and delegates lexical ranking only after
admission and lexical-request validation.

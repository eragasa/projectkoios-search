# AuthorityBoundEvidenceRetrievalRequest

`AuthorityBoundEvidenceRetrievalRequest` is the frozen, slotted production input
to authority-bound lexical retrieval. It binds one exact replay-current
`AuthorityBoundEvidenceAdmissionResult` to one exact bounded
`EvidenceRetrievalRequest`. Its identity commits to both request identities and
the References authority checkpoint, leaving the retrieval Actionizer stateless.

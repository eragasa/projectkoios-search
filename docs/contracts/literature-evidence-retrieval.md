# Literature evidence retrieval

Status: extracted candidate.

The literature-review retrieval slice requires both an explicit purpose and an
explicit corpus role. `LiteratureEvidenceBundleService` accepts only the
`literature_review` purpose and always issues `reference`-only requests. It has
no fallback to manuscripts, generated text, problem material, or other roles.

The service deterministically deduplicates passages, bounds query and bundle
sizes, limits repeated passages from one source, and assigns bundle-local
`E1`-style labels. `SqliteFtsReferenceEvidenceIndex` is a read-only adapter for
the demonstrated local FTS5 schema. It exposes source and passage identities,
page data, citation metadata, score, and bounded evidence text, but not private
filesystem locators.

Retrieval results are candidate evidence. Retrieval does not establish claim
support, perform equation verification, create a human disposition, or admit a
source for another retrieval purpose.

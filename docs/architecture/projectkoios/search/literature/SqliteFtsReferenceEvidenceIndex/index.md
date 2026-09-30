# `SqliteFtsReferenceEvidenceIndex`

This class is a read-only `PurposeScopedEvidenceIndex` adapter for the
demonstrated SQLite FTS5 schema. Construction rejects symlinks, missing or
non-file paths, missing required tables/views, and failed integrity checks.

Search accepts only literature-review/reference requests, creates an OR query
from unique case-folded Unicode word terms, filters the database to reference
documents, and returns at most one ranked passage per source. Connections use
SQLite URI read-only mode plus `query_only`; the class never writes the index.

# `PageSearchIndex`

Fail-closed read-only owner operation. Construction validates index identity and
integrity; `status()` exposes readiness/coverage and `search()` performs bounded,
stably ordered SQLite FTS5/BM25 retrieval without leaking storage details.

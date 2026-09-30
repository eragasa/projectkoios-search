# `in_memory_chunk_index` implementation

`add_chunks` appends the supplied iterable to an in-memory list. Search lowercases
and whitespace-splits the query, then scores each chunk by counting query-term
entries that occur as substrings of the lowercased chunk text.

```mermaid
flowchart LR
    Query["query and limit"] --> Guard{"limit > 0 and terms exist?"}
    Guard -- no --> Empty["empty list"]
    Guard -- yes --> Score["substring score each stored chunk"]
    Score --> Filter["retain positive scores"]
    Filter --> Sort["stable score-descending sort"]
    Sort --> Limit["return first limit results"]
```

A non-positive limit, empty query, or query without whitespace-delimited terms
returns an empty list. Equal-score results retain insertion order because the
score-only descending sort is stable. This module does not apply corpus-role or
purpose admission.

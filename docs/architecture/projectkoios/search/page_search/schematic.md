# Page-search schematic

```mermaid
flowchart LR
    I[Search typed chunking result] --> B[PageSearchBuildDocument]
    P[Pending catalog metadata] --> B
    B --> V[PageSearchBuildPlan validation]
    V --> C[Page-local sanitized chunks]
    C --> S[(Private staged SQLite)]
    S --> F[FTS5 rebuild and checks]
    F -->|atomic replace| L[(Live derived index)]
    A[API/Web] --> O[PageSearchIndex owner operation]
    O -->|read-only/query-only| L
    O --> R[Bounded safe BM25 DTOs]
```

The build path accepts typed owner results rather than transcript or publication
JSON. Projected text blocks enter page-local chunks in source order; equations,
media, paths, and publication payloads never enter storage or public results.

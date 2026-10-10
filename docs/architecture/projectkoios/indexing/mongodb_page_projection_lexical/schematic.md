# `mongodb_page_projection_lexical` schematic

```mermaid
flowchart TB
    Database["injected Mongo Database capability"] --> Projector["MongoPageProjectionLexicalProjector"]
    Chunk["PageProjectionLexicalChunk protocol"] --> Projector
    Projector --> C["page_projection_chunks<br/>immutable generation scope"]
    Projector --> P["lexical_term_postings<br/>immutable generation scope"]
    Projector --> S["lexical_statistics<br/>immutable generation scope"]
    Projector --> G["lexical_generations<br/>metadata + active pointer"]
    C --> Verify["count + identity + canonical manifest verification"]
    P --> Verify
    S --> Verify
    G --> Verify
    Verify --> CAS["single-document active pointer CAS"]
    G --> Retriever["MongoPageProjectionLexicalRetriever"]
    P --> Retriever
    S --> Retriever
    Request["bounded lexical request"] --> Retriever
    Retriever --> Result["generation-bound deterministic BM25 result"]
    Projector -. "no connection ownership" .-> Secret["endpoint / authentication"]
    Retriever -. "no dependency" .-> Excluded["Ingestion / vectors / models / API / workflow"]
```

Generation documents remain invisible until complete verification and the
single active-pointer compare-and-set. No collection rename, drop, delete, or
multi-document transaction participates in the path.

# `projectkoios.search` package schematic

```mermaid
flowchart TB
    Ingestion["Ingestion PageProjectionResult"] --> Chunking["page_projection_chunking"]
    Chunking --> SearchChunks["Search-owned chunks"]
    SearchChunks --> Lexical["page_projection_lexical structural boundary"]
    Facade["projectkoios.search facade"] --> Evidence["evidence_retrieval"]
    Facade --> Literature["literature"]
    Facade --> Models["models"]
    Facade --> Protocols["protocols"]
    Facade --> Service["service"]
    Literature --> Models
    Protocols --> Models
    Service --> Protocols
    Service --> Models
    Indexing["projectkoios.indexing"] --> Protocols
    Indexing --> Models
    Evidence -. "no conversion path" .-> Literature
    Evidence -. "no conversion path" .-> Models
    Chunking -. "no import" .-> Models
    Chunking -. "no import" .-> Protocols
    Chunking -. "not facade-exported" .-> Facade
    Lexical -. "no import" .-> Ingestion
    Lexical -. "not facade-exported" .-> Facade
    MongoLexical["indexing.mongodb_page_projection_lexical"] --> Lexical
```

Solid arrows represent imports, derivation, or facade exports. Dotted
relationships are explicit non-integration boundaries. Page-projection
chunking is the sole Ingestion-dependent module and remains independent of
indexing and retrieval; the authoring family neither wraps nor silently
converts the other prototype records.

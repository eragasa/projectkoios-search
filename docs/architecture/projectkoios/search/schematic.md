# `projectkoios.search` package schematic

```mermaid
flowchart TB
    Ingestion["Ingestion PageProjectionResult"] --> Chunking["page_projection_chunking"]
    Chunking --> SearchChunks["Search-owned chunks"]
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
```

Solid arrows represent imports, derivation, or facade exports. Dotted
relationships are explicit non-integration boundaries. Page-projection
chunking is the sole Ingestion-dependent module and remains independent of
indexing and retrieval; the authoring family neither wraps nor silently
converts the other prototype records.

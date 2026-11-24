# `projectkoios.search` package schematic

```mermaid
flowchart TB
    Ingestion["Ingestion PageProjectionResult"] --> Chunking["page_projection_chunking"]
    Enrichment["Ingestion public enrichment"] --> Authority["authority_bound_evidence"]
    References["References accepted Search authority"] --> Authority
    Chunking --> SearchChunks["Search-owned chunks"]
    SearchChunks --> Authority
    SearchChunks --> Lexical["page_projection_lexical structural boundary"]
    Evidence --> Authority
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
    Authority -. "not facade-exported" .-> Facade
    MongoLexical["indexing.mongodb_page_projection_lexical"] --> Lexical
```

Solid arrows represent imports, derivation, or facade exports. Dotted
relationships are explicit non-integration boundaries. Page-projection
chunking and authority admission are the only Ingestion-dependent modules and
use separate exact public leaves. The authority module composes rather than
mutates candidate-capable evidence records; unrelated indexing and retrieval
remain independent of producer packages.

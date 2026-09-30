# `projectkoios.search` package schematic

```mermaid
flowchart TB
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
```

Solid arrows represent imports or facade exports. Dotted relationships are
explicit non-integration boundaries: the authoring family neither wraps nor
silently converts the other prototype records.

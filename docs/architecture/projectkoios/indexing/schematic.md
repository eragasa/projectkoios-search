# `projectkoios.indexing` package schematic

```mermaid
flowchart LR
    Facade["projectkoios.indexing facade"] --> Chunk["in_memory_chunk_index"]
    Facade --> Scoped["in_memory_role_scoped_index"]
    Chunk --> SearchModels["projectkoios.search.models"]
    Scoped --> SearchModels
    Chunk --> TextChunk["projectkoios.chunking.TextChunk"]
    Scoped --> TextChunk
    Mongo["mongodb_page_projection_lexical<br/>direct leaf"] --> Lexical["search.page_projection_lexical"]
    Database["injected Mongo Database"] --> Mongo
    Mongo -. "not facade-exported" .-> Facade
```

The package provides implementations for Search-owned result and request
boundaries without moving those boundaries into the indexing package. The
Mongo leaf is imported directly so the facade remains independent of persistent
connection capabilities.

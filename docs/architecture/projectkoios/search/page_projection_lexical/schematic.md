# `page_projection_lexical` schematic

```mermaid
flowchart LR
    Chunk["exact Search PageProjectionChunk"] --> Protocol["PageProjectionLexicalChunk structural protocol"]
    Protocol --> Tokenizer["versioned tokenizer"]
    Protocol --> Corpus["canonical chunk manifest / corpus ID"]
    Tokenizer --> Index["index ID: corpus + tokenizer + schema + BM25"]
    Corpus --> Generation["immutable generation"]
    Index --> Generation
    Request["bounded search request"] --> QueryTerms["ordered unique terms"]
    QueryTerms --> Hit["ranked lexical hit"]
    Generation --> Result["generation-bound result"]
    Hit --> Result
    Protocol -. "no import" .-> Ingestion["Ingestion"]
    Result -. "no authority" .-> Excluded["API / workflow / publication / models"]
```

Solid arrows show deterministic derivation or containment. Dotted arrows record
hard dependency and authority exclusions. Persistence adapters consume these
contracts but are not imported by this module.

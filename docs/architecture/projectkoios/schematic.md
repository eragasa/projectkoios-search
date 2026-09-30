# `projectkoios` namespace schematic

```mermaid
flowchart LR
    Namespace["projectkoios namespace"] --> Search["projectkoios.search"]
    Namespace --> Indexing["projectkoios.indexing"]
    Base["projectkoios.base"] --> Search
    Chunking["projectkoios.chunking"] --> Search
    Chunking --> Indexing
    Search --> Indexing
    Search --> Consumers["explicit downstream consumers"]
    Indexing --> Consumers
```

`projectkoios.base` and `projectkoios.chunking` are shared dependency-owned
boundaries. This repository's indexing implementations consume Search-owned
models while both package facades remain explicit. Neither package acquires
product authority from the namespace.

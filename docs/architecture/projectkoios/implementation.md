# `projectkoios` namespace implementation

The package is distributed as a namespace package from `src/python`. This
repository implements Search-owned modules while the `projectkoios` dependency
supplies shared thin base objects and existing chunking records.

```mermaid
classDiagram
    class DataObjectModel
    class DataObjectActionRequest
    class DataObjectActionResult
    class DataObjectActionizer
    class TextChunk
    class PageProjectionResult
    class PageProjectionChunkingModule
    class SearchPackage["projectkoios.search"]
    class IndexingPackage["projectkoios.indexing"]

    DataObjectModel <|-- DataObjectActionRequest
    DataObjectModel <|-- DataObjectActionResult
    DataObjectActionizer --> DataObjectActionRequest
    DataObjectActionizer --> DataObjectActionResult
    SearchPackage ..> DataObjectModel
    SearchPackage ..> DataObjectActionizer
    PageProjectionChunkingModule ..> PageProjectionResult : exact leaf
    SearchPackage o-- PageProjectionChunkingModule
    SearchPackage ..> TextChunk
    IndexingPackage ..> TextChunk
    IndexingPackage ..> SearchPackage : models
```

Implementation modules import shared boundaries from their owning modules.
Only `projectkoios.search.page_projection_chunking` imports the Ingestion-owned
`PageProjectionResult`; Search indexing and retrieval modules remain independent
of Ingestion. `projectkoios.search` and `projectkoios.indexing` use explicit
initializers; the namespace root itself has no initializer or implementation
behavior.

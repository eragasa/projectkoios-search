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
    class SearchPackage["projectkoios.search"]

    DataObjectModel <|-- DataObjectActionRequest
    DataObjectModel <|-- DataObjectActionResult
    DataObjectActionizer --> DataObjectActionRequest
    DataObjectActionizer --> DataObjectActionResult
    SearchPackage ..> DataObjectModel
    SearchPackage ..> DataObjectActionizer
```

Implementation modules import shared boundaries from their owning modules.
The namespace initializer does not contain implementation behavior.

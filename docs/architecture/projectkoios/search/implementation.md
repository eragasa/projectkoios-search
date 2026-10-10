# `projectkoios.search` package implementation

The package initializer re-exports the established explicit inventory and keeps
all behavior in named modules. Authoring records import shared ABCs from
`projectkoios.base` and do not import the other search models. The
`page_projection_chunking` leaf remains a direct public module rather than a
facade export: this prevents ordinary indexing or retrieval imports from loading
Ingestion.

```mermaid
classDiagram
    class SearchFacade["projectkoios.search"]
    class PageProjectionChunkingModule["page_projection_chunking"]
    class PageProjectionResult
    class EvidenceRetrievalModule["evidence_retrieval"]
    class LiteratureModule["literature"]
    class ModelsModule["models"]
    class ProtocolsModule["protocols"]
    class ServiceModule["service"]

    PageProjectionChunkingModule --> PageProjectionResult : exact leaf input
    SearchFacade --> EvidenceRetrievalModule : re-export
    SearchFacade --> LiteratureModule : re-export
    SearchFacade --> ModelsModule : re-export
    SearchFacade --> ProtocolsModule : re-export
    SearchFacade --> ServiceModule : re-export
    LiteratureModule ..> ModelsModule : RetrievalPurpose
    ProtocolsModule ..> ModelsModule : request/results
    ServiceModule ..> ProtocolsModule : injected boundaries
    ServiceModule ..> ModelsModule : request/results
    EvidenceRetrievalModule .. LiteratureModule : independent
    EvidenceRetrievalModule .. ModelsModule : independent
```

Facade exports preserve each defining module's class identity; the initializer
defines no classes of its own. The sole Ingestion dependency is the exact
`PageProjectionResult` import inside `page_projection_chunking`; indexing and
retrieval modules do not import that module. The package owns no API transport,
persistence, generation, workflow, rights decision, publication, or
target-document behavior. Public implementation classes are documented at
exact defining-module paths.

# `projectkoios.search` package implementation

The package initializer re-exports the established explicit inventory and keeps
all behavior in named modules. Authoring records import shared ABCs from
`projectkoios.base` and do not import the other search models. The
`page_projection_chunking`, `authority_bound_evidence`, and backend-neutral
`page_projection_lexical` remain direct public modules rather than facade
exports: this prevents ordinary imports from loading Ingestion, References, or
persistent adapters.

```mermaid
classDiagram
    class SearchFacade["projectkoios.search"]
    class PageProjectionChunkingModule["page_projection_chunking"]
    class PageProjectionResult
    class PageProjectionLexicalModule["page_projection_lexical"]
    class MongoLexicalModule["indexing.mongodb_page_projection_lexical"]
    class EvidenceRetrievalModule["evidence_retrieval"]
    class AuthorityBoundEvidenceModule["authority_bound_evidence"]
    class LiteratureModule["literature"]
    class ModelsModule["models"]
    class ProtocolsModule["protocols"]
    class ServiceModule["service"]

    PageProjectionChunkingModule --> PageProjectionResult : exact leaf input
    PageProjectionChunkingModule ..> PageProjectionLexicalModule : concrete values satisfy protocol
    AuthorityBoundEvidenceModule --> PageProjectionChunkingModule : exact A
    AuthorityBoundEvidenceModule --> EvidenceRetrievalModule : existing item/retriever
    MongoLexicalModule --> PageProjectionLexicalModule : contracts
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
defines no classes of its own. Ingestion dependencies are limited to the exact
`PageProjectionResult` import inside `page_projection_chunking` and public
enrichment modules inside `authority_bound_evidence`; indexing and unrelated
retrieval modules import neither leaf. The package owns no API transport,
persistence, workflow, rights decision,
publication, or target-document behavior. `page_projection_lexical` owns only
backend-neutral immutable generation values; Mongo persistence is owned by the
separate indexing module. Public implementation classes are documented at exact
defining-module paths.

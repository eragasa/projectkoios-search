# `PageProjectionLexicalChunk`

`PageProjectionLexicalChunk` is the Search-owned runtime-checkable structural
protocol consumed by lexical projectors. It exposes exact chunk identity,
complete page-projection lineage, source/document/evidence and citation
identities, physical and printed page location, page-local order, closed style,
exact text, text SHA-256, and UTF-8 byte length.

It is read-only and defines no constructor or mapping. Concrete
`PageProjectionChunk` values satisfy it without importing their defining module
from a persistence adapter, so it introduces no duplicate DTO and no Ingestion
dependency.

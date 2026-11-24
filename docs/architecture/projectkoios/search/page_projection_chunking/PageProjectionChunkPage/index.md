# `PageProjectionChunkPage`

Immutable Search-owned physical-page descriptor derived from an exact typed page
projection. It retains the zero-based physical index and optional printed label,
and exposes the corresponding one-based physical page number. Chunking results
use these descriptors to preserve empty pages without exposing Ingestion types
to downstream Search modules.

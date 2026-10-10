"""Identity tests for immutable lexical generation metadata."""

from __future__ import annotations

from dataclasses import replace

import pytest
from projectkoios.search.page_projection_lexical import (
    PageProjectionLexicalGeneration,
)


def _generation() -> PageProjectionLexicalGeneration:
    """Return one internally consistent synthetic lexical generation.

    Returns
    -------
    PageProjectionLexicalGeneration
        Small bounded generation suitable for identity tests.
    """

    return PageProjectionLexicalGeneration(
        corpus_id=f"page-projection-lexical-corpus:sha256:{'a' * 64}",
        index_id=f"page-projection-lexical-index:sha256:{'b' * 64}",
        schema_id="projectkoios.search.mongodb-page-projection-lexical-index:1.0",
        tokenizer_id=(
            "projectkoios.search.page-projection-lexical-tokenizer:1.0"
        ),
        projector_id=(
            "projectkoios.search.mongodb-page-projection-lexical-indexer:1.0"
        ),
        chunk_manifest_sha256="d" * 64,
        index_manifest_sha256="e" * 64,
        chunk_count=2,
        posting_count=4,
        term_count=4,
        total_document_length=4,
    )


def test__generation_id__is_deterministic_and_content_sensitive() -> None:
    """Bind every immutable corpus, index, processor, and count field."""

    generation = _generation()

    assert replace(generation) == generation
    assert generation.generation_id.startswith(
        "page-projection-lexical-generation:sha256:"
    )
    assert replace(generation, posting_count=5).generation_id != (
        generation.generation_id
    )


def test__init__rejects_malformed_identity_and_counts() -> None:
    """Reject invalid identity text, digest shape, and negative counts."""

    generation = _generation()

    with pytest.raises(ValueError, match="corpus ID"):
        replace(generation, corpus_id="")
    with pytest.raises(ValueError, match="chunk manifest SHA-256"):
        replace(generation, chunk_manifest_sha256="not-a-digest")
    with pytest.raises(ValueError, match="nonnegative"):
        replace(generation, term_count=-1)

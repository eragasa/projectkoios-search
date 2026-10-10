"""Contract tests for :class:`PageProjectionChunk`.

These tests separate resolvable global provenance fields from the source-local
material used for chunk identity and exercise the closed style/value grammar.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import cast

import pytest
from projectkoios.search.page_projection_chunking import (
    PageProjectionChunk,
    PageProjectionChunker,
    PageProjectionChunkStyle,
)

from .fixture.chunking import derive_chunking_result


def test__provenance__preserves_complete_resolvable_bindings() -> None:
    """Retain all upstream result and source identifiers on every chunk.

    Notes
    -----
    Some retained global identifiers deliberately do not enter ``chunk_id``;
    they remain available so downstream consumers can resolve the exact input.
    """

    result = derive_chunking_result()
    projection = result.request.projection_result

    for chunk in result.chunks:
        assert chunk.page_projection_result_id == projection.result_id
        assert chunk.source_id == projection.source_id.value
        assert chunk.document_id == projection.document_id.value
        assert chunk.source_result_id == projection.source_result_id
        assert (
            chunk.artifact_verification_result_id
            == projection.artifact_verification_result_id
        )
        assert (
            chunk.reading_projection_result_id
            == projection.projection_result_id.value
        )
        assert (
            chunk.reading_inventory_id == projection.reading_inventory_id.value
        )
        assert chunk.PROCESSOR_ID == result.chunker_implementation_id
        assert chunk.PROCESSOR_VERSION == result.chunker_implementation_version
        assert (
            chunk.text_sha256
            == hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
        )
        assert chunk.text_utf8_bytes == len(chunk.text.encode("utf-8"))


def test__chunk_id__is_source_local_not_global_result_position() -> None:
    """Keep local identity stable when only complete-result bindings change.

    Notes
    -----
    Changing the source block-or-caption identity remains identity-significant;
    changing provider/global generation references alone does not renumber the
    otherwise identical source-local chunk.
    """

    chunk = next(iter(derive_chunking_result().chunks))
    rebound = replace(
        chunk,
        page_projection_result_id=f"projection:sha256:{'1' * 64}",
        document_id=f"document:sha256:{'2' * 64}",
        source_result_id=f"source-result:sha256:{'3' * 64}",
        artifact_verification_result_id=f"verification:sha256:{'4' * 64}",
        reading_projection_result_id=f"reading-result:sha256:{'5' * 64}",
        reading_inventory_id=f"reading-inventory:sha256:{'6' * 64}",
        page_projection_page_id=f"projected-page:sha256:{'7' * 64}",
    )
    changed_source = replace(
        chunk,
        source_evidence_id=f"reading-text-block:sha256:{'8' * 64}",
    )

    assert rebound.chunk_id == chunk.chunk_id
    assert changed_source.chunk_id != chunk.chunk_id


def test__chunk_id__binds_fixed_processor_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Change chunk identity when the fixed processor version changes.

    Parameters
    ----------
    monkeypatch
        Pytest helper used to simulate a future processor version without
        changing the production constant permanently.
    """

    chunk = next(iter(derive_chunking_result().chunks))
    monkeypatch.setattr(PageProjectionChunk, "PROCESSOR_VERSION", "2.0")

    changed = replace(chunk)

    assert changed.PROCESSOR_ID == PageProjectionChunker.IMPLEMENTATION_ID
    assert changed.PROCESSOR_VERSION == "2.0"
    assert changed.chunk_id != chunk.chunk_id


def test__init__requires_exact_style_and_bounded_values() -> None:
    """Accept the closed heading style and reject malformed public values.

    Notes
    -----
    Reusing every other field from a valid derived chunk isolates each public
    constructor invariant from unrelated fixture setup.
    """

    chunk = next(iter(derive_chunking_result().chunks))
    values = {
        field: getattr(chunk, field)
        for field in (
            "page_projection_result_id",
            "source_id",
            "document_id",
            "source_result_id",
            "artifact_verification_result_id",
            "reading_projection_result_id",
            "reading_inventory_id",
            "page_projection_page_id",
            "source_page_id",
            "page_location_id",
            "physical_page_index",
            "printed_page_label",
            "page_projection_block_id",
            "source_evidence_id",
            "order_index",
            "style",
            "text",
        )
    }

    heading = PageProjectionChunk(
        **(
            values
            | {
                "style": PageProjectionChunkStyle.HEADING,
                "text": "Synthetic heading",
            }
        )
    )
    assert heading.style is PageProjectionChunkStyle.HEADING
    assert heading.chunk_id != chunk.chunk_id

    with pytest.raises(TypeError, match="PageProjectionChunkStyle"):
        PageProjectionChunk(
            **(values | {"style": cast(PageProjectionChunkStyle, "paragraph")})
        )
    with pytest.raises(ValueError, match="nonnegative"):
        PageProjectionChunk(**(values | {"order_index": -1}))
    with pytest.raises(ValueError, match="nonempty"):
        PageProjectionChunk(**(values | {"text": ""}))

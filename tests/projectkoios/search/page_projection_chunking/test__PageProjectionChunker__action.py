"""Behavior tests for :class:`PageProjectionChunker` action execution.

These tests exercise the exact typed producer boundary and the fixed one-block
per-chunk policy. They intentionally avoid indexing, retrieval, persistence,
and application composition.
"""

from __future__ import annotations

import hashlib
import json

import pytest
from projectkoios.base import (
    DataObjectActionizer,
    DataObjectActionRequest,
    DataObjectActionResult,
)
from projectkoios.search.page_projection_chunking import (
    PageProjectionChunker,
    PageProjectionChunkingRequest,
    PageProjectionChunkStyle,
)

from .fixture.chunking import (
    INPUT_BYTES,
    INPUT_FIXTURE,
    INPUT_GIT_BLOB,
    INPUT_SHA256,
    derive_chunking_result,
    git_blob_oid,
)
from .fixture.result import (
    build_page_projection_result,
    observe_page_projection_result,
)


def test__action__accepts_exact_reconstructed_producer_fixture() -> None:
    """Verify copied bytes and their independently reconstructed typed value.

    Notes
    -----
    Byte identity is checked before semantic observation so a permissive JSON
    parser cannot conceal producer-fixture drift.
    """

    content = INPUT_FIXTURE.read_bytes()

    assert len(content) == INPUT_BYTES
    assert hashlib.sha256(content).hexdigest() == INPUT_SHA256
    assert git_blob_oid(content) == INPUT_GIT_BLOB
    assert not content.endswith(b"\n")
    expected = json.loads(content)
    assert observe_page_projection_result(build_page_projection_result()) == (
        expected
    )


def test__action__is_pure_and_deterministic() -> None:
    """Require identical action results for one immutable exact request.

    Notes
    -----
    The assertions also preserve the thin base-object classification required
    by the Project Koios action boundary.
    """

    projection = build_page_projection_result()
    request = PageProjectionChunkingRequest(projection_result=projection)
    chunker = PageProjectionChunker()

    first = chunker.action(request=request)
    second = chunker.action(request=request)

    assert isinstance(request, DataObjectActionRequest)
    assert isinstance(chunker, DataObjectActionizer)
    assert isinstance(first, DataObjectActionResult)
    assert first == second
    assert first.request is request
    assert first.chunks.page_projection_result_id == projection.result_id
    assert first.result_id.startswith("page-projection-chunking-result:sha256:")


def test__action__emits_one_exact_chunk_per_projected_block() -> None:
    """Preserve exact block order, text, style, and source evidence identity.

    Notes
    -----
    The synthetic source also contains table and equation evidence. Their
    absence here proves Search consumes only blocks admitted by Ingestion's
    page projection instead of reaching back into broader source evidence.
    """

    result = derive_chunking_result()
    projection = result.request.projection_result
    projected_blocks = tuple(
        block for page in projection.pages for block in page.blocks
    )
    chunks = tuple(result.chunks)

    assert len(chunks) == len(projected_blocks) == 2
    assert tuple(value.text for value in chunks) == (
        "Canonical paragraph.",
        "Figure title",
    )
    assert tuple(value.style for value in chunks) == (
        PageProjectionChunkStyle.PARAGRAPH,
        PageProjectionChunkStyle.FIGURE_CAPTION,
    )
    assert tuple(value.order_index for value in chunks) == (0, 1)
    assert tuple(value.page_projection_block_id for value in chunks) == tuple(
        value.block_id for value in projected_blocks
    )
    assert tuple(value.source_evidence_id for value in chunks) == tuple(
        value.source_id.value for value in projected_blocks
    )
    assert all(value.physical_page_index == 0 for value in chunks)
    assert all(value.physical_page_number == 1 for value in chunks)
    assert all(value.printed_page_label == "1" for value in chunks)
    assert not any(hasattr(value, "chunk_index") for value in chunks)


def test__action__rejects_post_construction_source_mutation() -> None:
    """Reject a request whose upstream result identity changed after creation.

    Notes
    -----
    Direct mutation is deliberate adversarial test setup against a frozen data
    object; ordinary callers cannot perform this through the public API.
    """

    projection = build_page_projection_result()
    request = PageProjectionChunkingRequest(projection_result=projection)
    object.__setattr__(
        projection,
        "result_id",
        f"page-projection-result:sha256:{'e' * 64}",
    )

    with pytest.raises(ValueError, match="stale or invalid"):
        PageProjectionChunker().action(request=request)

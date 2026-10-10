"""Validation tests for :class:`PageProjectionChunkInventory`.

The inventory owns complete canonical source order while still representing a
valid projection whose pages contain no admitted text blocks.
"""

from __future__ import annotations

import pytest
from projectkoios.search.page_projection_chunking import (
    PageProjectionChunkInventory,
)

from .fixture.chunking import derive_chunking_result
from .fixture.result import build_page_projection_result


def test__init__rejects_reordered_chunks() -> None:
    """Reject valid chunks supplied in reverse source order.

    Notes
    -----
    Chunk identities remain individually valid, so this isolates the inventory's
    canonical ordering invariant.
    """

    valid = derive_chunking_result()
    chunks = tuple(valid.chunks)

    with pytest.raises(ValueError, match="canonical source order"):
        PageProjectionChunkInventory(
            page_projection_result_id=(
                valid.request.projection_result.result_id
            ),
            chunks=(chunks[1], chunks[0]),
        )


def test__init__binds_empty_source_without_fabricating_chunks() -> None:
    """Represent an empty derivation without inventing placeholder text.

    Notes
    -----
    The projection-result identity distinguishes empty inventories belonging to
    different exact upstream results.
    """

    projection = build_page_projection_result()

    inventory = PageProjectionChunkInventory(
        page_projection_result_id=projection.result_id,
        chunks=(),
    )

    assert not inventory
    assert tuple(inventory) == ()
    assert inventory.text_utf8_bytes == 0
    assert inventory.inventory_id.startswith(
        "page-projection-chunk-inventory:sha256:"
    )

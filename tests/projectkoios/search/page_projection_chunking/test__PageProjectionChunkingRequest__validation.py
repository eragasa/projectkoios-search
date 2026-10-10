"""Validation tests for :class:`PageProjectionChunkingRequest`.

The request accepts only the exact current-schema Ingestion leaf result and
revalidates its deterministic identity before any Search chunk derivation.
"""

from __future__ import annotations

from typing import cast

import pytest
from projectkoios.ingestion.page.projection.result import PageProjectionResult
from projectkoios.search.page_projection_chunking import (
    PageProjectionChunkingRequest,
)

from .fixture.result import build_page_projection_result


def test__init__rejects_wrong_or_stale_projection_result() -> None:
    """Reject a wrong runtime type and an identity-stale exact result.

    Notes
    -----
    The forced mutation bypasses frozen-dataclass protection solely to verify
    the receiving boundary independently checks current identity.
    """

    with pytest.raises(TypeError, match="must be PageProjectionResult"):
        PageProjectionChunkingRequest(
            # The cast crosses static typing intentionally to exercise the
            # production runtime boundary with an invalid concrete value.
            projection_result=cast(PageProjectionResult, object())
        )

    projection = build_page_projection_result()
    object.__setattr__(
        projection,
        "result_id",
        f"page-projection-result:sha256:{'f' * 64}",
    )
    with pytest.raises(ValueError, match="identity is stale"):
        PageProjectionChunkingRequest(projection_result=projection)

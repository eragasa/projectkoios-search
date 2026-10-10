"""Validation tests for bounded page-projection lexical requests."""

from __future__ import annotations

from dataclasses import replace

import pytest
from projectkoios.search.page_projection_lexical import (
    PageProjectionLexicalSearchRequest,
)


def test__request_id__binds_query_and_applied_bounds() -> None:
    """Derive stable request identity from exact query and bounds."""

    request = PageProjectionLexicalSearchRequest(
        query="deterministic evidence",
        limit=10,
        maximum_candidate_postings=1_000,
    )

    assert replace(request) == request
    assert request.request_id.startswith(
        "page-projection-lexical-search-request:sha256:"
    )
    assert replace(request, limit=9).request_id != request.request_id


def test__init__rejects_blank_query_and_invalid_bounds() -> None:
    """Reject requests that cannot execute within fixed resource ceilings."""

    with pytest.raises(ValueError, match="query"):
        PageProjectionLexicalSearchRequest(query=" ")
    with pytest.raises(ValueError, match="result limit"):
        PageProjectionLexicalSearchRequest(query="evidence", limit=0)
    with pytest.raises(ValueError, match="candidate posting"):
        PageProjectionLexicalSearchRequest(
            query="evidence",
            maximum_candidate_postings=0,
        )
    with pytest.raises(ValueError, match="valid UTF-8"):
        PageProjectionLexicalSearchRequest(query="invalid\ud800")
    with pytest.raises(ValueError, match="lexical term bound"):
        PageProjectionLexicalSearchRequest(
            query=" ".join(f"term{index}" for index in range(257))
        )

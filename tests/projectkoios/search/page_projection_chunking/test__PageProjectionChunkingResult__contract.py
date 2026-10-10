"""Contract tests for :class:`PageProjectionChunkingResult`.

The tests freeze exact Search-owned observation bytes and independently verify
that a caller cannot substitute an altered chunk inventory for the derived one.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest
from projectkoios.search.page_projection_chunking import (
    PageProjectionChunkingResult,
    PageProjectionChunkInventory,
)

from .fixture.chunking import (
    EXPECTED_BYTES,
    EXPECTED_FIXTURE,
    EXPECTED_GIT_BLOB,
    EXPECTED_SHA256,
    derive_chunking_result,
    git_blob_oid,
    observe_chunking_result,
)


def test__result_id__matches_search_owned_expected_fixture() -> None:
    """Match exact expected bytes and every observed deterministic field.

    Notes
    -----
    Byte length, content digest, Git blob identity, and missing terminal newline
    are separate assertions so fixture drift is diagnosable before JSON parsing.
    """

    content = EXPECTED_FIXTURE.read_bytes()

    assert len(content) == EXPECTED_BYTES
    assert hashlib.sha256(content).hexdigest() == EXPECTED_SHA256
    assert git_blob_oid(content) == EXPECTED_GIT_BLOB
    assert not content.endswith(b"\n")
    assert observe_chunking_result(derive_chunking_result()) == json.loads(
        content
    )


def test__init__rejects_altered_derived_chunks() -> None:
    """Reject a complete-looking inventory containing changed text.

    Notes
    -----
    Reconstructing the altered chunk gives it a self-consistent new chunk ID;
    result validation must still detect divergence from the deterministic
    derivation.
    """

    valid = derive_chunking_result()
    chunks = tuple(valid.chunks)
    altered = replace(chunks[0], text="Altered paragraph.")

    with pytest.raises(ValueError, match="deterministic derivation"):
        PageProjectionChunkingResult(
            request=valid.request,
            chunks=PageProjectionChunkInventory(
                page_projection_result_id=(
                    valid.request.projection_result.result_id
                ),
                chunks=(altered, chunks[1]),
            ),
            chunker_implementation_id=valid.chunker_implementation_id,
            chunker_implementation_version=(
                valid.chunker_implementation_version
            ),
        )

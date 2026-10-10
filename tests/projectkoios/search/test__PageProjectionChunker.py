from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest
from projectkoios.base import (
    DataObjectActionizer,
    DataObjectActionRequest,
    DataObjectActionResult,
)
from projectkoios.search.page_projection_chunking import (
    PageProjectionChunk,
    PageProjectionChunker,
    PageProjectionChunkingRequest,
    PageProjectionChunkingResult,
    PageProjectionChunkInventory,
    PageProjectionChunkStyle,
)

from tests.projectkoios.search.page_projection_support.result import (
    build_page_projection_result,
    observe_page_projection_result,
)

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures/page_projection"
_INPUT_FIXTURE = _FIXTURES / "current-schema-v1.json"
_EXPECTED_FIXTURE = _FIXTURES / "current-schema-v1.expected-chunks.json"
_INPUT_BYTES = 2_554
_INPUT_SHA256 = (
    "9e725777ebb87f5a9fc69ebbcb64d69c98aabd205a3e92c95840c13fac538c8f"
)
_INPUT_GIT_BLOB = "16ccea4aef4154531d2963f9cca7c41280ee19c7"
_EXPECTED_BYTES = 4_993
_EXPECTED_SHA256 = (
    "8b11964d2c5f870eb30f642c45094ce41c1b92d42055c51707b345391630e7b8"
)
_EXPECTED_GIT_BLOB = "4fc157fb52e9f72ad0d5a5a9e932e27849aa326c"


def _git_blob_oid(content: bytes) -> str:
    framed = f"blob {len(content)}\0".encode("ascii") + content
    return hashlib.sha1(framed, usedforsecurity=False).hexdigest()


def _derive() -> PageProjectionChunkingResult:
    request = PageProjectionChunkingRequest(
        projection_result=build_page_projection_result()
    )
    return PageProjectionChunker().action(request=request)


def _observation(result: PageProjectionChunkingResult) -> dict[str, object]:
    request = result.request
    chunks = [
        {
            "artifact_verification_result_id": (
                value.artifact_verification_result_id
            ),
            "chunk_id": value.chunk_id,
            "contract_version": value.CONTRACT_VERSION,
            "document_id": value.document_id,
            "order_index": value.order_index,
            "page_location_id": value.page_location_id,
            "page_projection_block_id": value.page_projection_block_id,
            "page_projection_page_id": value.page_projection_page_id,
            "page_projection_result_id": value.page_projection_result_id,
            "physical_page_index": value.physical_page_index,
            "physical_page_number": value.physical_page_number,
            "policy_id": value.POLICY_ID,
            "policy_version": value.POLICY_VERSION,
            "printed_page_label": value.printed_page_label,
            "processor_id": value.PROCESSOR_ID,
            "processor_version": value.PROCESSOR_VERSION,
            "reading_inventory_id": value.reading_inventory_id,
            "reading_projection_result_id": (
                value.reading_projection_result_id
            ),
            "source_evidence_id": value.source_evidence_id,
            "source_id": value.source_id,
            "source_page_id": value.source_page_id,
            "source_result_id": value.source_result_id,
            "style": value.style.value,
            "text": value.text,
            "text_sha256": value.text_sha256,
            "text_utf8_bytes": value.text_utf8_bytes,
        }
        for value in result.chunks
    ]
    return {
        "fixture_kind": (
            "projectkoios.search.page-projection-chunking-observation"
        ),
        "fixture_schema": 1,
        "input_fixture": {
            "git_blob_oid": _INPUT_GIT_BLOB,
            "kind": "projectkoios.ingestion.page-projection-observation",
            "schema": 1,
            "sha256": _INPUT_SHA256,
        },
        "request": {
            "contract_name": request.CONTRACT_NAME,
            "contract_version": request.CONTRACT_VERSION,
            "page_projection_result_id": request.projection_result.result_id,
            "policy_id": request.POLICY_ID,
            "policy_version": request.POLICY_VERSION,
            "request_id": request.request_id,
        },
        "result": {
            "chunk_count": len(result.chunks),
            "chunk_inventory_id": result.chunks.inventory_id,
            "chunker_implementation_id": result.chunker_implementation_id,
            "chunker_implementation_version": (
                result.chunker_implementation_version
            ),
            "chunks": chunks,
            "contract_name": result.CONTRACT_NAME,
            "contract_version": result.CONTRACT_VERSION,
            "result_id": result.result_id,
            "text_utf8_bytes": result.chunks.text_utf8_bytes,
        },
    }


def test__producer_fixture__is_exact_and_reconstructs_typed_result() -> None:
    content = _INPUT_FIXTURE.read_bytes()

    assert len(content) == _INPUT_BYTES
    assert hashlib.sha256(content).hexdigest() == _INPUT_SHA256
    assert _git_blob_oid(content) == _INPUT_GIT_BLOB
    assert not content.endswith(b"\n")
    expected = json.loads(content)
    assert observe_page_projection_result(build_page_projection_result()) == (
        expected
    )


def test__chunker__is_pure_deterministic_action_contract() -> None:
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


def test__chunker__emits_one_exact_chunk_per_projected_block() -> None:
    result = _derive()
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


def test__chunker__preserves_complete_resolvable_provenance() -> None:
    result = _derive()
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


def test__chunking_result__matches_search_owned_expected_fixture() -> None:
    content = _EXPECTED_FIXTURE.read_bytes()

    assert len(content) == _EXPECTED_BYTES
    assert hashlib.sha256(content).hexdigest() == _EXPECTED_SHA256
    assert _git_blob_oid(content) == _EXPECTED_GIT_BLOB
    assert not content.endswith(b"\n")
    assert _observation(_derive()) == json.loads(content)


def test__request__rejects_wrong_or_stale_projection_result() -> None:
    with pytest.raises(TypeError, match="must be PageProjectionResult"):
        PageProjectionChunkingRequest(
            projection_result=cast(object, object())  # type: ignore[arg-type]
        )

    projection = build_page_projection_result()
    object.__setattr__(
        projection,
        "result_id",
        f"page-projection-result:sha256:{'f' * 64}",
    )
    with pytest.raises(ValueError, match="identity is stale"):
        PageProjectionChunkingRequest(projection_result=projection)


def test__action__rejects_post_construction_source_mutation() -> None:
    projection = build_page_projection_result()
    request = PageProjectionChunkingRequest(projection_result=projection)
    object.__setattr__(
        projection,
        "result_id",
        f"page-projection-result:sha256:{'e' * 64}",
    )

    with pytest.raises(ValueError, match="stale or invalid"):
        PageProjectionChunker().action(request=request)


def test__result__rejects_altered_or_reordered_chunks() -> None:
    valid = _derive()
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

    with pytest.raises(ValueError, match="canonical source order"):
        PageProjectionChunkInventory(
            page_projection_result_id=(
                valid.request.projection_result.result_id
            ),
            chunks=(chunks[1], chunks[0]),
        )


def test__chunk_identity__is_source_local_not_global_result_position() -> None:
    chunk = next(iter(_derive().chunks))
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


def test__chunk_identity__binds_fixed_processor_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunk = next(iter(_derive().chunks))
    monkeypatch.setattr(PageProjectionChunk, "PROCESSOR_VERSION", "2.0")

    changed = replace(chunk)

    assert changed.PROCESSOR_ID == PageProjectionChunker.IMPLEMENTATION_ID
    assert changed.PROCESSOR_VERSION == "2.0"
    assert changed.chunk_id != chunk.chunk_id


def test__chunk__requires_exact_style_and_bounded_values() -> None:
    chunk = next(iter(_derive().chunks))
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


def test__empty_inventory__binds_source_without_fabricating_chunks() -> None:
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

"""Shared observations for page-projection chunking tests.

The helpers in this module keep fixture paths, immutable byte identities, and
Search result observation logic in one test-local owner. They do not serialize
production objects or define a public wire format.

Notes
-----
The Ingestion-owned JSON is compared byte-for-byte before its reconstructed
``PageProjectionResult`` is passed to the production chunker. The Search-owned
JSON freezes the corresponding deterministic output only for conformance tests.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from projectkoios.search.page_projection_chunking import (
    PageProjectionChunker,
    PageProjectionChunkingRequest,
    PageProjectionChunkingResult,
)

from .result import build_page_projection_result

FIXTURES = Path(__file__).resolve().parents[4] / "fixtures/page_projection"
INPUT_FIXTURE = FIXTURES / "current-schema-v1.json"
EXPECTED_FIXTURE = FIXTURES / "current-schema-v1.expected-chunks.json"
INPUT_BYTES = 2_554
INPUT_SHA256 = (
    "9e725777ebb87f5a9fc69ebbcb64d69c98aabd205a3e92c95840c13fac538c8f"
)
INPUT_GIT_BLOB = "16ccea4aef4154531d2963f9cca7c41280ee19c7"
EXPECTED_BYTES = 4_993
EXPECTED_SHA256 = (
    "8b11964d2c5f870eb30f642c45094ce41c1b92d42055c51707b345391630e7b8"
)
EXPECTED_GIT_BLOB = "4fc157fb52e9f72ad0d5a5a9e932e27849aa326c"


def git_blob_oid(content: bytes) -> str:
    """Return the Git blob identity for exact fixture bytes.

    Parameters
    ----------
    content
        Exact bytes whose canonical Git blob framing must be identified.

    Returns
    -------
    str
        Lowercase SHA-1 Git object identity for the framed blob.
    """

    # Git hashes the object type and decimal byte length before the payload.
    framed = f"blob {len(content)}\0".encode("ascii") + content
    return hashlib.sha1(framed, usedforsecurity=False).hexdigest()


def derive_chunking_result() -> PageProjectionChunkingResult:
    """Derive the Search result from the reconstructed producer fixture.

    Returns
    -------
    PageProjectionChunkingResult
        Fresh deterministic output from the production request and chunker.
    """

    request = PageProjectionChunkingRequest(
        projection_result=build_page_projection_result()
    )
    return PageProjectionChunker().action(request=request)


def observe_chunking_result(
    result: PageProjectionChunkingResult,
) -> dict[str, object]:
    """Project a Search result into the expected test-only observation.

    Parameters
    ----------
    result
        Exact Search-owned result to compare with the frozen expectation.

    Returns
    -------
    dict[str, object]
        JSON-compatible observation containing contract and provenance fields.
    """

    request = result.request
    # Preserve action output order; sorting chunks would hide ordering defects.
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
            "git_blob_oid": INPUT_GIT_BLOB,
            "kind": "projectkoios.ingestion.page-projection-observation",
            "schema": 1,
            "sha256": INPUT_SHA256,
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

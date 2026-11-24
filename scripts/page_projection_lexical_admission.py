"""Shared bounded runtime for current-schema lexical corpus-union admission.

The two operator modules in this package call this implementation for a
read-only preflight and for one revision-bound activation. Ingestion decoding is
owned exclusively by its strict typed publication loader. Search derives exact
block-local chunks, preserves every active chunk, and owns Mongo generation,
activation, replay, and retrieval validation.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from projectkoios.indexing.mongodb_page_projection_lexical import (
    MongoDocument,
    MongoPageProjectionLexicalActiveSnapshot,
    MongoPageProjectionLexicalError,
    MongoPageProjectionLexicalProjector,
    MongoPageProjectionLexicalRetriever,
)
from projectkoios.search.page_projection_chunking import (
    PageProjectionChunk,
    PageProjectionChunker,
    PageProjectionChunkingRequest,
    PageProjectionChunkInventory,
    PageProjectionChunkStyle,
)
from projectkoios.search.page_projection_lexical import (
    PageProjectionLexicalGeneration,
    PageProjectionLexicalIdentity,
    PageProjectionLexicalSearchHit,
    PageProjectionLexicalSearchRequest,
)
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

DATABASE_NAME: Final[str] = "projectkoios_search_development"
STORAGE_TARGET_ID: Final[str] = "projectkoios.search.mongodb.development"
CAPABILITY_ID: Final[str] = (
    "mongodb-database-capability:sha256:"
    "d0286175d36e6de1ccba5c608cf2c6a78ca3f817e2d42f8e318b50f51c58a520"
)
CONNECTION_URI_DESCRIPTOR: Final[int] = 3
MAXIMUM_SECRET_BYTES: Final[int] = 8_192
MAXIMUM_OUTPUT_BYTES: Final[int] = 65_536
MAXIMUM_PROJECTION_COUNT: Final[int] = 1_024
ABSENT: Final[str] = "absent"

_COMMON_ARGUMENT_NAMES: Final[tuple[str, ...]] = (
    "--database-name",
    "--storage-target-id",
    "--capability-id",
    "--connection-uri-fd",
    "--publication-root",
    "--source-sha256",
    "--source-byte-length",
    "--source-media-type",
    "--source-artifact-id",
    "--pipeline-configuration-id",
    "--publication-id",
    "--receipt-id",
    "--receipt-sha256",
    "--receipt-byte-length",
    "--payload-id",
    "--payload-sha256",
    "--payload-byte-length",
    "--page-projection-result-id",
    "--enrichment-result-id",
    "--maximum-payload-bytes",
    "--expected-load-request-id",
    "--expected-load-result-id",
    "--expected-source-page-count",
    "--expected-source-chunk-count",
    "--physical-page-index-first",
    "--physical-page-index-last",
    "--expected-page-inventory-sha256",
    "--expected-block-identity-inventory-sha256",
    "--expected-enrichment-identity-inventory-sha256",
    "--expected-page-count",
    "--expected-chunk-count",
    "--expected-document-text-utf8-bytes",
    "--expected-enrichment-available-count",
    "--expected-enrichment-unavailable-count",
    "--expected-paragraph-count",
    "--expected-heading-count",
    "--expected-figure-caption-count",
    "--expected-chunking-request-id",
    "--expected-source-chunk-inventory-id",
    "--expected-chunk-inventory-id",
    "--expected-chunking-result-id",
    "--expected-chunk-selection-id",
    "--expected-document-chunk-manifest-sha256",
    "--smoke-query",
    "--smoke-limit",
)
_ADMISSION_ARGUMENT_NAMES: Final[tuple[str, ...]] = (
    *_COMMON_ARGUMENT_NAMES,
    "--expected-active-generation-id",
    "--expected-active-pointer-revision",
    "--expected-union-generation-id",
    "--expected-union-chunk-manifest-sha256",
    "--expected-union-chunk-count",
)

_PRELIGHT_SUCCESS_KEYS: Final[frozenset[str]] = frozenset(
    {
        "active_chunk_count",
        "active_chunk_manifest_sha256",
        "active_corpus_id",
        "active_generation_id",
        "active_index_id",
        "active_pointer_revision",
        "active_projection_chunk_counts",
        "active_state",
        "added_chunk_count",
        "capability_id",
        "block_identity_inventory_sha256",
        "chunk_inventory_id",
        "chunk_selection_id",
        "chunking_request_id",
        "chunking_result_id",
        "database_name",
        "document_chunk_count",
        "document_chunk_manifest_sha256",
        "document_style_counts",
        "document_text_utf8_bytes",
        "enrichment_available_count",
        "enrichment_identity_inventory_sha256",
        "enrichment_result_id",
        "enrichment_unavailable_count",
        "load_request_id",
        "load_result_id",
        "overlapping_chunk_count",
        "page_count",
        "page_inventory_sha256",
        "page_projection_result_id",
        "physical_page_index_first",
        "physical_page_index_last",
        "phase",
        "preflight_id",
        "publication_id",
        "schema_id",
        "status",
        "source_chunk_count",
        "source_chunk_inventory_id",
        "source_page_count",
        "storage_target_id",
        "tokenizer_id",
        "union_chunk_count",
        "union_chunk_manifest_sha256",
        "union_corpus_id",
        "union_generation_id",
        "union_index_id",
        "union_index_manifest_sha256",
        "union_posting_count",
        "union_term_count",
        "union_total_document_length",
    }
)
_ADMISSION_SUCCESS_KEYS: Final[frozenset[str]] = frozenset(
    {
        "active_generation_id_after",
        "active_generation_id_before",
        "active_pointer_revision_after",
        "active_pointer_revision_before",
        "active_state_before",
        "added_chunk_count",
        "admission_result_id",
        "capability_id",
        "chunk_inventory_id",
        "chunk_selection_id",
        "chunking_result_id",
        "corpus_id",
        "database_name",
        "disposition",
        "generation_id",
        "hit_locators",
        "index_id",
        "load_result_id",
        "overlapping_chunk_count",
        "page_projection_result_id",
        "phase",
        "physical_page_index_first",
        "physical_page_index_last",
        "pointer_changed",
        "posting_count",
        "preserved_chunk_count",
        "projection_chunk_counts_after",
        "projection_chunk_counts_before",
        "publication_id",
        "replay_generation_id",
        "replay_pointer_revision",
        "retrieval_replay_result_id",
        "retrieval_result_id",
        "schema_id",
        "smoke_query_request_id",
        "status",
        "storage_target_id",
        "target_chunk_count",
        "term_count",
        "tokenizer_id",
        "total_document_length",
        "union_chunk_count",
        "union_chunk_manifest_sha256",
    }
)
_FAILURE_KEYS: Final[frozenset[str]] = frozenset(
    {"category", "exit_code", "phase", "status"}
)
_HIT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "artifact_verification_result_id",
        "chunk_id",
        "document_id",
        "matched_terms",
        "order_index",
        "page_location_id",
        "page_projection_block_id",
        "page_projection_page_id",
        "page_projection_result_id",
        "physical_page_index",
        "physical_page_number",
        "printed_page_label",
        "rank",
        "reading_inventory_id",
        "reading_projection_result_id",
        "score_hex",
        "source_evidence_id",
        "source_id",
        "source_page_id",
        "source_result_id",
        "style",
        "text_sha256",
        "text_utf8_bytes",
    }
)
_PERSISTED_CHUNK_KEYS: Final[frozenset[str]] = frozenset(
    {
        "_id",
        "artifact_verification_result_id",
        "chunk_id",
        "document_id",
        "document_length",
        "document_type",
        "generation_id",
        "order_index",
        "page_location_id",
        "page_projection_block_id",
        "page_projection_page_id",
        "page_projection_result_id",
        "physical_page_index",
        "physical_page_number",
        "printed_page_label",
        "reading_inventory_id",
        "reading_projection_result_id",
        "source_evidence_id",
        "source_id",
        "source_page_id",
        "source_result_id",
        "style",
        "text",
        "text_sha256",
        "text_utf8_bytes",
    }
)


class AdmissionInvocationError(ValueError):
    """Reject a nonallowlisted command invocation or secret channel."""


class AdmissionOwnerLoadError(RuntimeError):
    """Report a redacted strict owner-loader failure."""


class AdmissionInventoryError(RuntimeError):
    """Report a redacted exact-inventory mismatch."""


class AdmissionStateError(RuntimeError):
    """Report malformed or drifted Mongo lexical state."""


class AdmissionCASError(RuntimeError):
    """Report a revision-bound pointer activation failure."""


class AdmissionRetrievalError(RuntimeError):
    """Report retrieval or locator-validation failure."""


class AdmissionOutputError(RuntimeError):
    """Report an unsafe output record before it is emitted."""


@dataclass(frozen=True, slots=True, kw_only=True)
class AdmissionArguments:
    """Retain one exact immutable typed-load and inventory invocation."""

    publication_root: Path
    source_sha256: str
    source_byte_length: int
    source_media_type: str
    source_artifact_id: str
    pipeline_configuration_id: str
    publication_id: str
    receipt_id: str
    receipt_sha256: str
    receipt_byte_length: int
    payload_id: str
    payload_sha256: str
    payload_byte_length: int
    page_projection_result_id: str
    enrichment_result_id: str
    maximum_payload_bytes: int
    expected_load_request_id: str
    expected_load_result_id: str
    expected_source_page_count: int
    expected_source_chunk_count: int
    physical_page_index_first: int
    physical_page_index_last: int
    expected_page_inventory_sha256: str
    expected_block_identity_inventory_sha256: str
    expected_enrichment_identity_inventory_sha256: str
    expected_page_count: int
    expected_chunk_count: int
    expected_document_text_utf8_bytes: int
    expected_enrichment_available_count: int
    expected_enrichment_unavailable_count: int
    expected_paragraph_count: int
    expected_heading_count: int
    expected_figure_caption_count: int
    expected_chunking_request_id: str
    expected_source_chunk_inventory_id: str
    expected_chunk_inventory_id: str
    expected_chunking_result_id: str
    expected_chunk_selection_id: str
    expected_document_chunk_manifest_sha256: str
    smoke_query: str
    smoke_limit: int
    expected_active_generation_id: str | None = None
    expected_active_pointer_revision: int | None = None
    expected_union_generation_id: str | None = None
    expected_union_chunk_manifest_sha256: str | None = None
    expected_union_chunk_count: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class LoadedDocument:
    """Retain validated owner-load and Search chunking evidence."""

    load_request_id: str
    load_result_id: str
    chunking_request_id: str
    source_chunk_inventory_id: str
    chunk_inventory_id: str
    chunking_result_id: str
    chunk_selection_id: str
    source_page_count: int
    source_chunk_count: int
    physical_page_index_first: int
    physical_page_index_last: int
    page_inventory_sha256: str
    block_identity_inventory_sha256: str
    enrichment_identity_inventory_sha256: str
    page_count: int
    document_text_utf8_bytes: int
    enrichment_available_count: int
    enrichment_unavailable_count: int
    chunks: tuple[PageProjectionChunk, ...]
    style_counts: dict[str, int]
    chunk_manifest_sha256: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UnionPlan:
    """Bind one observed active corpus to a deterministic complete union."""

    active_chunks: tuple[PageProjectionChunk, ...]
    union_chunks: tuple[PageProjectionChunk, ...]
    generation: PageProjectionLexicalGeneration
    added_chunk_count: int
    overlapping_chunk_count: int


def _require_int(value: str, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value, 10)
    except ValueError as error:
        raise AdmissionInvocationError from error
    if str(parsed) != value or not minimum <= parsed <= maximum:
        raise AdmissionInvocationError
    return parsed


def _require_text(value: str, *, maximum_bytes: int = 4_096) -> str:
    if not value or value != value.strip():
        raise AdmissionInvocationError
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise AdmissionInvocationError from error
    if len(encoded) > maximum_bytes or any(
        character in {"\r", "\n"}
        or unicodedata.category(character).startswith("C")
        for character in value
    ):
        raise AdmissionInvocationError
    return value


def _require_sha256(value: str) -> str:
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise AdmissionInvocationError
    return value


def _require_identity(value: str, *, prefix: str) -> str:
    checked = _require_text(value, maximum_bytes=1_024)
    if not checked.startswith(prefix):
        raise AdmissionInvocationError
    return checked


def parse_arguments(
    *, argv: tuple[str, ...], admission: bool
) -> AdmissionArguments:
    """Parse one closed positional-pair command contract."""

    names = _ADMISSION_ARGUMENT_NAMES if admission else _COMMON_ARGUMENT_NAMES
    if len(argv) != len(names) * 2 or tuple(argv[::2]) != names:
        raise AdmissionInvocationError
    raw = dict(zip(names, argv[1::2], strict=True))
    if (
        raw["--database-name"] != DATABASE_NAME
        or raw["--storage-target-id"] != STORAGE_TARGET_ID
        or raw["--capability-id"] != CAPABILITY_ID
        or raw["--connection-uri-fd"] != str(CONNECTION_URI_DESCRIPTOR)
        or raw["--source-media-type"] != "application/pdf"
    ):
        raise AdmissionInvocationError
    publication_root_text = _require_text(raw["--publication-root"])
    publication_root = Path(publication_root_text)
    if not publication_root.is_absolute():
        raise AdmissionInvocationError
    expected_active_generation_id: str | None = None
    expected_active_pointer_revision: int | None = None
    expected_union_generation_id: str | None = None
    expected_union_chunk_manifest_sha256: str | None = None
    expected_union_chunk_count: int | None = None
    if admission:
        generation_text = raw["--expected-active-generation-id"]
        revision_text = raw["--expected-active-pointer-revision"]
        if generation_text == ABSENT or revision_text == ABSENT:
            if generation_text != ABSENT or revision_text != ABSENT:
                raise AdmissionInvocationError
        else:
            expected_active_generation_id = _require_identity(
                generation_text,
                prefix="page-projection-lexical-generation:sha256:",
            )
            expected_active_pointer_revision = _require_int(
                revision_text, minimum=1, maximum=1_000_000_000
            )
        expected_union_generation_id = _require_identity(
            raw["--expected-union-generation-id"],
            prefix="page-projection-lexical-generation:sha256:",
        )
        expected_union_chunk_manifest_sha256 = _require_sha256(
            raw["--expected-union-chunk-manifest-sha256"]
        )
        expected_union_chunk_count = _require_int(
            raw["--expected-union-chunk-count"],
            minimum=1,
            maximum=1_000_000,
        )
    source_page_count = _require_int(
        raw["--expected-source-page-count"], minimum=1, maximum=1_000_000
    )
    source_chunk_count = _require_int(
        raw["--expected-source-chunk-count"], minimum=1, maximum=1_000_000
    )
    page_index_first = _require_int(
        raw["--physical-page-index-first"], minimum=0, maximum=999_999
    )
    page_index_last = _require_int(
        raw["--physical-page-index-last"], minimum=0, maximum=999_999
    )
    selected_page_count = _require_int(
        raw["--expected-page-count"], minimum=1, maximum=1_000_000
    )
    selected_chunk_count = _require_int(
        raw["--expected-chunk-count"], minimum=1, maximum=1_000_000
    )
    available_count = _require_int(
        raw["--expected-enrichment-available-count"],
        minimum=0,
        maximum=1_000_000,
    )
    unavailable_count = _require_int(
        raw["--expected-enrichment-unavailable-count"],
        minimum=0,
        maximum=1_000_000,
    )
    style_count = sum(
        _require_int(raw[name], minimum=0, maximum=1_000_000)
        for name in (
            "--expected-paragraph-count",
            "--expected-heading-count",
            "--expected-figure-caption-count",
        )
    )
    payload_byte_length = _require_int(
        raw["--payload-byte-length"], minimum=1, maximum=1_000_000_000
    )
    maximum_payload_bytes = _require_int(
        raw["--maximum-payload-bytes"], minimum=1, maximum=1_000_000_000
    )
    if (
        page_index_first > page_index_last
        or page_index_last >= source_page_count
        or selected_page_count != page_index_last - page_index_first + 1
        or selected_chunk_count > source_chunk_count
        or available_count + unavailable_count != selected_chunk_count
        or style_count != selected_chunk_count
        or maximum_payload_bytes < payload_byte_length
    ):
        raise AdmissionInvocationError
    return AdmissionArguments(
        publication_root=publication_root,
        source_sha256=_require_sha256(raw["--source-sha256"]),
        source_byte_length=_require_int(
            raw["--source-byte-length"], minimum=1, maximum=1_000_000_000
        ),
        source_media_type=raw["--source-media-type"],
        source_artifact_id=_require_identity(
            raw["--source-artifact-id"], prefix="managed-artifact:sha256:"
        ),
        pipeline_configuration_id=_require_identity(
            raw["--pipeline-configuration-id"],
            prefix="page-projection-publication-pipeline:sha256:",
        ),
        publication_id=_require_identity(
            raw["--publication-id"],
            prefix="page-projection-publication:sha256:",
        ),
        receipt_id=_require_identity(
            raw["--receipt-id"],
            prefix="page-projection-publication-receipt:sha256:",
        ),
        receipt_sha256=_require_sha256(raw["--receipt-sha256"]),
        receipt_byte_length=_require_int(
            raw["--receipt-byte-length"], minimum=1, maximum=1_000_000
        ),
        payload_id=_require_identity(
            raw["--payload-id"],
            prefix="page-projection-publication-payload:sha256:",
        ),
        payload_sha256=_require_sha256(raw["--payload-sha256"]),
        payload_byte_length=payload_byte_length,
        page_projection_result_id=_require_identity(
            raw["--page-projection-result-id"],
            prefix="page-projection-result:sha256:",
        ),
        enrichment_result_id=_require_identity(
            raw["--enrichment-result-id"],
            prefix="page-projection-evidence-enrichment-result:sha256:",
        ),
        maximum_payload_bytes=maximum_payload_bytes,
        expected_load_request_id=_require_identity(
            raw["--expected-load-request-id"],
            prefix="page-projection-publication-load-request:sha256:",
        ),
        expected_load_result_id=_require_identity(
            raw["--expected-load-result-id"],
            prefix="page-projection-publication-load-result:sha256:",
        ),
        expected_source_page_count=_require_int(
            raw["--expected-source-page-count"],
            minimum=1,
            maximum=1_000_000,
        ),
        expected_source_chunk_count=_require_int(
            raw["--expected-source-chunk-count"],
            minimum=1,
            maximum=1_000_000,
        ),
        physical_page_index_first=_require_int(
            raw["--physical-page-index-first"],
            minimum=0,
            maximum=999_999,
        ),
        physical_page_index_last=_require_int(
            raw["--physical-page-index-last"],
            minimum=0,
            maximum=999_999,
        ),
        expected_page_inventory_sha256=_require_sha256(
            raw["--expected-page-inventory-sha256"]
        ),
        expected_block_identity_inventory_sha256=_require_sha256(
            raw["--expected-block-identity-inventory-sha256"]
        ),
        expected_enrichment_identity_inventory_sha256=_require_sha256(
            raw["--expected-enrichment-identity-inventory-sha256"]
        ),
        expected_page_count=_require_int(
            raw["--expected-page-count"], minimum=1, maximum=1_000_000
        ),
        expected_chunk_count=_require_int(
            raw["--expected-chunk-count"], minimum=1, maximum=1_000_000
        ),
        expected_document_text_utf8_bytes=_require_int(
            raw["--expected-document-text-utf8-bytes"],
            minimum=1,
            maximum=1_000_000_000,
        ),
        expected_enrichment_available_count=_require_int(
            raw["--expected-enrichment-available-count"],
            minimum=0,
            maximum=1_000_000,
        ),
        expected_enrichment_unavailable_count=_require_int(
            raw["--expected-enrichment-unavailable-count"],
            minimum=0,
            maximum=1_000_000,
        ),
        expected_paragraph_count=_require_int(
            raw["--expected-paragraph-count"], minimum=0, maximum=1_000_000
        ),
        expected_heading_count=_require_int(
            raw["--expected-heading-count"], minimum=0, maximum=1_000_000
        ),
        expected_figure_caption_count=_require_int(
            raw["--expected-figure-caption-count"],
            minimum=0,
            maximum=1_000_000,
        ),
        expected_chunking_request_id=_require_identity(
            raw["--expected-chunking-request-id"],
            prefix="page-projection-chunking-request:sha256:",
        ),
        expected_source_chunk_inventory_id=_require_identity(
            raw["--expected-source-chunk-inventory-id"],
            prefix="page-projection-chunk-inventory:sha256:",
        ),
        expected_chunk_inventory_id=_require_identity(
            raw["--expected-chunk-inventory-id"],
            prefix="page-projection-chunk-inventory:sha256:",
        ),
        expected_chunking_result_id=_require_identity(
            raw["--expected-chunking-result-id"],
            prefix="page-projection-chunking-result:sha256:",
        ),
        expected_chunk_selection_id=_require_identity(
            raw["--expected-chunk-selection-id"],
            prefix="page-projection-chunk-selection:sha256:",
        ),
        expected_document_chunk_manifest_sha256=_require_sha256(
            raw["--expected-document-chunk-manifest-sha256"]
        ),
        smoke_query=_require_text(raw["--smoke-query"], maximum_bytes=2_000),
        smoke_limit=_require_int(raw["--smoke-limit"], minimum=1, maximum=20),
        expected_active_generation_id=expected_active_generation_id,
        expected_active_pointer_revision=expected_active_pointer_revision,
        expected_union_generation_id=expected_union_generation_id,
        expected_union_chunk_manifest_sha256=(
            expected_union_chunk_manifest_sha256
        ),
        expected_union_chunk_count=expected_union_chunk_count,
    )


def read_connection_uri() -> str:
    """Read and close the complete bounded URI from inherited FD 3 once."""

    value = bytearray()
    try:
        while len(value) <= MAXIMUM_SECRET_BYTES:
            part = os.read(
                CONNECTION_URI_DESCRIPTOR,
                MAXIMUM_SECRET_BYTES + 1 - len(value),
            )
            if not part:
                break
            value.extend(part)
    except OSError as error:
        raise AdmissionInvocationError from error
    finally:
        try:
            os.close(CONNECTION_URI_DESCRIPTOR)
        except OSError:
            pass
    if not value or len(value) > MAXIMUM_SECRET_BYTES:
        raise AdmissionInvocationError
    try:
        connection_uri = bytes(value).decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise AdmissionInvocationError from error
    finally:
        value.clear()
    if connection_uri != connection_uri.strip() or any(
        character in {"\r", "\n"}
        or unicodedata.category(character).startswith("C")
        for character in connection_uri
    ):
        raise AdmissionInvocationError
    return connection_uri


def _inventory_digest(material: object) -> str:
    """Hash one exact canonical owner-native inventory material value."""

    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8", errors="strict")
    return hashlib.sha256(encoded).hexdigest()


def _chunk_selection_id(
    *,
    chunking_result_id: str,
    source_chunk_inventory_id: str,
    chunk_inventory_id: str,
    physical_page_index_first: int,
    physical_page_index_last: int,
    page_inventory_sha256: str,
    block_identity_inventory_sha256: str,
    enrichment_identity_inventory_sha256: str,
    chunk_manifest_sha256: str,
    page_count: int,
    chunk_count: int,
    document_text_utf8_bytes: int,
) -> str:
    """Bind a complete deterministic physical-page chunk selection."""

    digest = _inventory_digest(
        {
            "block_identity_inventory_sha256": (
                block_identity_inventory_sha256
            ),
            "chunk_count": chunk_count,
            "chunk_inventory_id": chunk_inventory_id,
            "chunk_manifest_sha256": chunk_manifest_sha256,
            "chunking_result_id": chunking_result_id,
            "document_text_utf8_bytes": document_text_utf8_bytes,
            "enrichment_identity_inventory_sha256": (
                enrichment_identity_inventory_sha256
            ),
            "page_count": page_count,
            "page_inventory_sha256": page_inventory_sha256,
            "physical_page_index_first": physical_page_index_first,
            "physical_page_index_last": physical_page_index_last,
            "source_chunk_inventory_id": source_chunk_inventory_id,
            "type": "projectkoios.search.page-projection-chunk-selection",
            "version": "1.0",
        }
    )
    return f"page-projection-chunk-selection:sha256:{digest}"


def validate_document_inventory(
    *,
    arguments: AdmissionArguments,
    source_page_count: int,
    source_chunk_count: int,
    source_chunk_inventory_id: str,
    page_count: int,
    block_count: int,
    document_text_utf8_bytes: int,
    page_inventory_sha256: str,
    block_identity_inventory_sha256: str,
    enrichment_identity_inventory_sha256: str,
    enrichment_available_count: int,
    enrichment_unavailable_count: int,
    chunk_count: int,
    style_counts: dict[str, int],
    chunking_request_id: str,
    chunk_inventory_id: str,
    chunking_result_id: str,
    chunk_selection_id: str,
    chunk_manifest_sha256: str,
) -> None:
    """Require every operator-pinned source and selected inventory measure."""

    expected_style_counts = {
        "figure_caption": arguments.expected_figure_caption_count,
        "heading": arguments.expected_heading_count,
        "paragraph": arguments.expected_paragraph_count,
    }
    if (
        source_page_count != arguments.expected_source_page_count
        or source_chunk_count != arguments.expected_source_chunk_count
        or source_chunk_inventory_id
        != arguments.expected_source_chunk_inventory_id
        or page_count != arguments.expected_page_count
        or block_count != arguments.expected_chunk_count
        or chunk_count != arguments.expected_chunk_count
        or document_text_utf8_bytes
        != arguments.expected_document_text_utf8_bytes
        or page_inventory_sha256 != arguments.expected_page_inventory_sha256
        or block_identity_inventory_sha256
        != arguments.expected_block_identity_inventory_sha256
        or enrichment_identity_inventory_sha256
        != arguments.expected_enrichment_identity_inventory_sha256
        or enrichment_available_count
        != arguments.expected_enrichment_available_count
        or enrichment_unavailable_count
        != arguments.expected_enrichment_unavailable_count
        or {key: style_counts.get(key, 0) for key in expected_style_counts}
        != expected_style_counts
        or sum(style_counts.values()) != chunk_count
        or chunking_request_id != arguments.expected_chunking_request_id
        or chunk_inventory_id != arguments.expected_chunk_inventory_id
        or chunking_result_id != arguments.expected_chunking_result_id
        or chunk_selection_id != arguments.expected_chunk_selection_id
        or chunk_manifest_sha256
        != arguments.expected_document_chunk_manifest_sha256
    ):
        raise AdmissionInventoryError


def load_document(*, arguments: AdmissionArguments) -> LoadedDocument:
    """Strict-load owner types and derive the exact Search chunk inventory."""

    try:
        from projectkoios.ingestion.artifact.managed.media.type import (
            ManagedArtifactMediaType,
        )
        from projectkoios.ingestion.artifact.managed.reference import (
            ManagedArtifactReference,
        )
        from projectkoios.ingestion.integrations.disk.page.projection.publication.load.runtime import (  # noqa: E501
            DiskPageProjectionPublicationLoadRuntime,
        )
        from projectkoios.ingestion.page.projection.enrichment.record import (  # noqa: E501
            PageProjectionEvidenceEnrichment,
        )
        from projectkoios.ingestion.page.projection.publication.load.request import (  # noqa: E501
            PageProjectionPublicationLoadRequest,
        )
        from projectkoios.ingestion.page.projection.result import (
            PageProjectionResult,
        )
        from projectkoios.ingestion.sha256.hash import SHA256Hash

        source = ManagedArtifactReference(
            sha256=SHA256Hash(arguments.source_sha256),
            byte_length=arguments.source_byte_length,
            media_type=ManagedArtifactMediaType(arguments.source_media_type),
        )
        if source.artifact_id != arguments.source_artifact_id:
            raise AdmissionOwnerLoadError
        request = PageProjectionPublicationLoadRequest(
            source_artifact=source,
            expected_pipeline_configuration_id=(
                arguments.pipeline_configuration_id
            ),
            expected_publication_id=arguments.publication_id,
            expected_receipt_id=arguments.receipt_id,
            expected_receipt_sha256=SHA256Hash(arguments.receipt_sha256),
            expected_receipt_byte_length=arguments.receipt_byte_length,
            expected_payload_id=arguments.payload_id,
            expected_payload_sha256=SHA256Hash(arguments.payload_sha256),
            expected_payload_byte_length=arguments.payload_byte_length,
            expected_page_projection_result_id=(
                arguments.page_projection_result_id
            ),
            expected_enrichment_result_id=arguments.enrichment_result_id,
            maximum_payload_bytes=arguments.maximum_payload_bytes,
        )
        if request.request_id != arguments.expected_load_request_id:
            raise AdmissionOwnerLoadError
        loaded = (
            DiskPageProjectionPublicationLoadRuntime(
                publication_root=arguments.publication_root
            )
            .create_actionizer()
            .action(request=request)
        )
        if (
            loaded.result_id != arguments.expected_load_result_id
            or type(loaded.projection) is not PageProjectionResult
            or loaded.projection.result_id
            != arguments.page_projection_result_id
            or loaded.enrichment.result_id != arguments.enrichment_result_id
        ):
            raise AdmissionOwnerLoadError
    except AdmissionOwnerLoadError:
        raise
    except Exception as error:
        raise AdmissionOwnerLoadError from error
    try:
        chunking = PageProjectionChunker().action(
            request=PageProjectionChunkingRequest(
                projection_result=loaded.projection
            )
        )
        source_chunks = tuple(chunking.chunks)
        if len(loaded.enrichment.entries) != len(source_chunks):
            raise AdmissionInventoryError
        selected_pages = tuple(
            page
            for page in loaded.projection.pages
            if arguments.physical_page_index_first
            <= page.physical_page_index
            <= arguments.physical_page_index_last
        )
        if tuple(page.physical_page_index for page in selected_pages) != tuple(
            range(
                arguments.physical_page_index_first,
                arguments.physical_page_index_last + 1,
            )
        ):
            raise AdmissionInventoryError
        selected_page_ids = {page.page_id for page in selected_pages}
        selected_blocks = tuple(
            block for page in selected_pages for block in page.blocks
        )
        selected_block_ids = {block.block_id for block in selected_blocks}
        chunks = tuple(
            value
            for value in source_chunks
            if arguments.physical_page_index_first
            <= value.physical_page_index
            <= arguments.physical_page_index_last
        )
        if {
            value.page_projection_block_id for value in chunks
        } != selected_block_ids:
            raise AdmissionInventoryError
        selected_entries = tuple(
            entry
            for entry in loaded.enrichment.entries
            if entry.page_projection_page_id in selected_page_ids
        )
        if {
            entry.page_projection_block_id for entry in selected_entries
        } != selected_block_ids or len(selected_entries) != len(
            selected_block_ids
        ):
            raise AdmissionInventoryError
        page_inventory = [
            {
                "block_count": len(page.blocks),
                "block_inventory_id": page.blocks.inventory_id,
                "page_id": page.page_id,
                "page_location_id": page.page_location.location_id.value,
                "physical_page_index": page.physical_page_index,
                "physical_page_number": page.physical_page_number,
                "printed_page_label": page.printed_page_label,
                "projected_text_bytes": page.blocks.projected_text_bytes,
                "source_page_id": page.source_page_id.value,
            }
            for page in selected_pages
        ]
        block_identity_inventory = [
            {
                "block_id": block.block_id,
                "order_index": block.order_index,
                "source_id": block.source_id.value,
                "style": block.style.value,
            }
            for block in selected_blocks
        ]
        enrichment_identity_inventory = sorted(
            (
                {
                    "entry_id": entry.entry_id,
                    "page_projection_block_id": (
                        entry.page_projection_block_id
                    ),
                    "page_projection_page_id": entry.page_projection_page_id,
                    "source_evidence_id": entry.source_evidence_id,
                }
                for entry in selected_entries
            ),
            key=lambda value: value["page_projection_block_id"],
        )
        page_inventory_sha256 = _inventory_digest(page_inventory)
        block_identity_inventory_sha256 = _inventory_digest(
            block_identity_inventory
        )
        enrichment_identity_inventory_sha256 = _inventory_digest(
            enrichment_identity_inventory
        )
        selected_inventory = PageProjectionChunkInventory(
            page_projection_result_id=loaded.projection.result_id,
            chunks=chunks,
        )
        chunk_ids = tuple(value.chunk_id for value in chunks)
        style_counts = Counter(value.style.value for value in chunks)
        manifest_sha256 = PageProjectionLexicalIdentity.chunk_manifest_sha256(
            chunk_ids=chunk_ids
        )
        text_utf8_bytes = sum(value.text_utf8_bytes for value in chunks)
        if text_utf8_bytes != sum(
            page.blocks.projected_text_bytes for page in selected_pages
        ):
            raise AdmissionInventoryError
        selection_id = _chunk_selection_id(
            chunking_result_id=chunking.result_id,
            source_chunk_inventory_id=chunking.chunks.inventory_id,
            chunk_inventory_id=selected_inventory.inventory_id,
            physical_page_index_first=arguments.physical_page_index_first,
            physical_page_index_last=arguments.physical_page_index_last,
            page_inventory_sha256=page_inventory_sha256,
            block_identity_inventory_sha256=(block_identity_inventory_sha256),
            enrichment_identity_inventory_sha256=(
                enrichment_identity_inventory_sha256
            ),
            chunk_manifest_sha256=manifest_sha256,
            page_count=len(selected_pages),
            chunk_count=len(chunks),
            document_text_utf8_bytes=text_utf8_bytes,
        )
        available_count = sum(
            type(entry) is PageProjectionEvidenceEnrichment
            for entry in selected_entries
        )
        unavailable_count = len(selected_entries) - available_count
        validate_document_inventory(
            arguments=arguments,
            source_page_count=len(loaded.projection.pages),
            source_chunk_count=len(source_chunks),
            source_chunk_inventory_id=chunking.chunks.inventory_id,
            page_count=len(selected_pages),
            block_count=len(selected_blocks),
            document_text_utf8_bytes=text_utf8_bytes,
            page_inventory_sha256=page_inventory_sha256,
            block_identity_inventory_sha256=(block_identity_inventory_sha256),
            enrichment_identity_inventory_sha256=(
                enrichment_identity_inventory_sha256
            ),
            enrichment_available_count=available_count,
            enrichment_unavailable_count=unavailable_count,
            chunk_count=len(chunks),
            style_counts=dict(style_counts),
            chunking_request_id=chunking.request.request_id,
            chunk_inventory_id=selected_inventory.inventory_id,
            chunking_result_id=chunking.result_id,
            chunk_selection_id=selection_id,
            chunk_manifest_sha256=manifest_sha256,
        )
        return LoadedDocument(
            load_request_id=request.request_id,
            load_result_id=loaded.result_id,
            chunking_request_id=chunking.request.request_id,
            source_chunk_inventory_id=chunking.chunks.inventory_id,
            chunk_inventory_id=selected_inventory.inventory_id,
            chunking_result_id=chunking.result_id,
            chunk_selection_id=selection_id,
            source_page_count=len(loaded.projection.pages),
            source_chunk_count=len(source_chunks),
            physical_page_index_first=arguments.physical_page_index_first,
            physical_page_index_last=arguments.physical_page_index_last,
            page_inventory_sha256=page_inventory_sha256,
            block_identity_inventory_sha256=(block_identity_inventory_sha256),
            enrichment_identity_inventory_sha256=(
                enrichment_identity_inventory_sha256
            ),
            page_count=len(selected_pages),
            document_text_utf8_bytes=text_utf8_bytes,
            enrichment_available_count=available_count,
            enrichment_unavailable_count=unavailable_count,
            chunks=chunks,
            style_counts=dict(sorted(style_counts.items())),
            chunk_manifest_sha256=manifest_sha256,
        )
    except AdmissionInventoryError:
        raise
    except Exception as error:
        raise AdmissionInventoryError from error


def create_client(*, connection_uri: str) -> MongoClient[MongoDocument]:
    """Create the one allowlisted bounded development client."""

    return MongoClient(
        connection_uri,
        appname="projectkoios-search-page-projection-corpus-union-admission",
        connectTimeoutMS=5_000,
        serverSelectionTimeoutMS=5_000,
        socketTimeoutMS=30_000,
    )


def require_database(
    *, client: MongoClient[MongoDocument]
) -> Database[MongoDocument]:
    """Return the pinged fixed development database."""

    database = client.get_database(DATABASE_NAME)
    if database.command("ping").get("ok") != 1.0:
        raise AdmissionStateError
    return database


def _persisted_chunk(document: MongoDocument) -> PageProjectionChunk:
    """Reconstruct and compare one exact Search-owned stored chunk."""

    if (
        frozenset(document) != _PERSISTED_CHUNK_KEYS
        or document.get("document_type") != "page-projection-chunk"
    ):
        raise AdmissionStateError
    try:
        chunk = PageProjectionChunk(
            page_projection_result_id=cast(
                str, document["page_projection_result_id"]
            ),
            source_id=cast(str, document["source_id"]),
            document_id=cast(str, document["document_id"]),
            source_result_id=cast(str, document["source_result_id"]),
            artifact_verification_result_id=cast(
                str, document["artifact_verification_result_id"]
            ),
            reading_projection_result_id=cast(
                str, document["reading_projection_result_id"]
            ),
            reading_inventory_id=cast(str, document["reading_inventory_id"]),
            page_projection_page_id=cast(
                str, document["page_projection_page_id"]
            ),
            source_page_id=cast(str, document["source_page_id"]),
            page_location_id=cast(str, document["page_location_id"]),
            physical_page_index=cast(int, document["physical_page_index"]),
            printed_page_label=cast(str | None, document["printed_page_label"]),
            page_projection_block_id=cast(
                str, document["page_projection_block_id"]
            ),
            source_evidence_id=cast(str, document["source_evidence_id"]),
            order_index=cast(int, document["order_index"]),
            style=PageProjectionChunkStyle(cast(str, document["style"])),
            text=cast(str, document["text"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise AdmissionStateError from error
    if (
        chunk.chunk_id != document.get("chunk_id")
        or chunk.physical_page_number != document.get("physical_page_number")
        or chunk.text_sha256 != document.get("text_sha256")
        or chunk.text_utf8_bytes != document.get("text_utf8_bytes")
    ):
        raise AdmissionStateError
    return chunk


def verify_required_indexes(
    *, projector: MongoPageProjectionLexicalProjector
) -> None:
    """Read and require both exact unique index definitions without writes."""

    chunk_index = projector._chunks.index_information().get(
        "generation_chunk_unique"
    )
    posting_index = projector._postings.index_information().get(
        "generation_term_chunk_unique"
    )
    if (
        chunk_index is None
        or tuple(chunk_index.get("key", ()))
        != (("generation_id", 1), ("chunk_id", 1))
        or chunk_index.get("unique") is not True
        or posting_index is None
        or tuple(posting_index.get("key", ()))
        != (("generation_id", 1), ("term", 1), ("chunk_id", 1))
        or posting_index.get("unique") is not True
    ):
        raise AdmissionStateError


def active_chunks(
    *,
    projector: MongoPageProjectionLexicalProjector,
    snapshot: MongoPageProjectionLexicalActiveSnapshot,
) -> tuple[PageProjectionChunk, ...]:
    """Read and reconstruct every exact chunk in the observed active corpus."""

    if snapshot.generation is None:
        return ()
    projector._verify_persisted_generation(generation=snapshot.generation)
    documents = tuple(
        projector._chunks.find(
            {"generation_id": snapshot.generation.generation_id},
            sort=[("chunk_id", 1)],
        )
    )
    if len(documents) != snapshot.generation.chunk_count:
        raise AdmissionStateError
    chunks = tuple(_persisted_chunk(value) for value in documents)
    if len({value.chunk_id for value in chunks}) != len(chunks):
        raise AdmissionStateError
    return chunks


def projection_counts(
    chunks: tuple[PageProjectionChunk, ...],
) -> list[dict[str, object]]:
    """Return bounded complete projection/chunk counts."""

    counts = Counter(value.page_projection_result_id for value in chunks)
    if len(counts) > MAXIMUM_PROJECTION_COUNT:
        raise AdmissionStateError
    return [
        {"chunk_count": count, "page_projection_result_id": projection_id}
        for projection_id, count in sorted(counts.items())
    ]


def union_plan(
    *,
    projector: MongoPageProjectionLexicalProjector,
    snapshot: MongoPageProjectionLexicalActiveSnapshot,
    document: LoadedDocument,
) -> UnionPlan:
    """Preserve the observed corpus and add one complete exact publication."""

    existing = active_chunks(projector=projector, snapshot=snapshot)
    existing_by_id = {value.chunk_id: value for value in existing}
    target_by_id = {value.chunk_id: value for value in document.chunks}
    if len(target_by_id) != len(document.chunks):
        raise AdmissionInventoryError
    existing_target_ids = {
        value.chunk_id
        for value in existing
        if value.page_projection_result_id
        == document.chunks[0].page_projection_result_id
    }
    target_ids = set(target_by_id)
    if existing_target_ids and existing_target_ids != target_ids:
        raise AdmissionStateError
    overlap = existing_by_id.keys() & target_by_id.keys()
    if any(existing_by_id[value] != target_by_id[value] for value in overlap):
        raise AdmissionStateError
    combined = dict(existing_by_id)
    combined.update(target_by_id)
    union_chunks = tuple(combined[key] for key in sorted(combined))
    try:
        generation = projector._derive_documents(chunks=union_chunks)[0]
    except (MongoPageProjectionLexicalError, TypeError, ValueError) as error:
        raise AdmissionInventoryError from error
    return UnionPlan(
        active_chunks=existing,
        union_chunks=union_chunks,
        generation=generation,
        added_chunk_count=len(target_ids - existing_by_id.keys()),
        overlapping_chunk_count=len(overlap),
    )


def _identity(*, prefix: str, material: dict[str, object]) -> str:
    encoded = json.dumps(
        material,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8", errors="strict")
    return f"{prefix}:sha256:{hashlib.sha256(encoded).hexdigest()}"


def _snapshot_fields(
    snapshot: MongoPageProjectionLexicalActiveSnapshot,
) -> dict[str, object]:
    generation = snapshot.generation
    if generation is None:
        return {
            "active_chunk_count": 0,
            "active_chunk_manifest_sha256": None,
            "active_corpus_id": None,
            "active_generation_id": None,
            "active_index_id": None,
            "active_pointer_revision": None,
            "active_state": ABSENT,
        }
    return {
        "active_chunk_count": generation.chunk_count,
        "active_chunk_manifest_sha256": generation.chunk_manifest_sha256,
        "active_corpus_id": generation.corpus_id,
        "active_generation_id": generation.generation_id,
        "active_index_id": generation.index_id,
        "active_pointer_revision": snapshot.pointer_revision,
        "active_state": "present",
    }


def preflight_record(
    *,
    projector: MongoPageProjectionLexicalProjector,
    snapshot: MongoPageProjectionLexicalActiveSnapshot,
    document: LoadedDocument,
    plan: UnionPlan,
    publication_id: str,
    enrichment_result_id: str,
) -> dict[str, object]:
    """Build the strict read-only preflight success record."""

    generation = plan.generation
    record: dict[str, object] = {
        **_snapshot_fields(snapshot),
        "active_projection_chunk_counts": projection_counts(plan.active_chunks),
        "added_chunk_count": plan.added_chunk_count,
        "block_identity_inventory_sha256": (
            document.block_identity_inventory_sha256
        ),
        "capability_id": CAPABILITY_ID,
        "chunk_inventory_id": document.chunk_inventory_id,
        "chunk_selection_id": document.chunk_selection_id,
        "chunking_request_id": document.chunking_request_id,
        "chunking_result_id": document.chunking_result_id,
        "database_name": DATABASE_NAME,
        "document_chunk_count": len(document.chunks),
        "document_chunk_manifest_sha256": document.chunk_manifest_sha256,
        "document_style_counts": document.style_counts,
        "document_text_utf8_bytes": document.document_text_utf8_bytes,
        "enrichment_available_count": document.enrichment_available_count,
        "enrichment_identity_inventory_sha256": (
            document.enrichment_identity_inventory_sha256
        ),
        "enrichment_result_id": enrichment_result_id,
        "enrichment_unavailable_count": document.enrichment_unavailable_count,
        "load_request_id": document.load_request_id,
        "load_result_id": document.load_result_id,
        "overlapping_chunk_count": plan.overlapping_chunk_count,
        "page_count": document.page_count,
        "page_inventory_sha256": document.page_inventory_sha256,
        "page_projection_result_id": document.chunks[
            0
        ].page_projection_result_id,
        "physical_page_index_first": document.physical_page_index_first,
        "physical_page_index_last": document.physical_page_index_last,
        "phase": "read-only-preflight",
        "preflight_id": "",
        "publication_id": publication_id,
        "schema_id": projector.SCHEMA_ID,
        "source_chunk_count": document.source_chunk_count,
        "source_chunk_inventory_id": document.source_chunk_inventory_id,
        "source_page_count": document.source_page_count,
        "status": "verified",
        "storage_target_id": STORAGE_TARGET_ID,
        "tokenizer_id": projector._tokenizer.tokenizer_id,
        "union_chunk_count": generation.chunk_count,
        "union_chunk_manifest_sha256": generation.chunk_manifest_sha256,
        "union_corpus_id": generation.corpus_id,
        "union_generation_id": generation.generation_id,
        "union_index_id": generation.index_id,
        "union_index_manifest_sha256": generation.index_manifest_sha256,
        "union_posting_count": generation.posting_count,
        "union_term_count": generation.term_count,
        "union_total_document_length": generation.total_document_length,
    }
    record["preflight_id"] = _identity(
        prefix="page-projection-lexical-admission-preflight",
        material={
            key: value for key, value in record.items() if key != "preflight_id"
        },
    )
    validate_success_record(record=record, phase="read-only-preflight")
    return record


def _hit_locators(
    *,
    projector: MongoPageProjectionLexicalProjector,
    generation: PageProjectionLexicalGeneration,
    hits: tuple[PageProjectionLexicalSearchHit, ...],
) -> list[dict[str, object]]:
    locators: list[dict[str, object]] = []
    for hit in hits:
        chunk_id = hit.chunk_id
        document = projector._chunks.find_one(
            {"generation_id": generation.generation_id, "chunk_id": chunk_id}
        )
        if document is None:
            raise AdmissionRetrievalError
        chunk = _persisted_chunk(document)
        locator = {
            "artifact_verification_result_id": (
                chunk.artifact_verification_result_id
            ),
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "matched_terms": list(hit.matched_terms),
            "order_index": chunk.order_index,
            "page_location_id": chunk.page_location_id,
            "page_projection_block_id": chunk.page_projection_block_id,
            "page_projection_page_id": chunk.page_projection_page_id,
            "page_projection_result_id": chunk.page_projection_result_id,
            "physical_page_index": chunk.physical_page_index,
            "physical_page_number": chunk.physical_page_number,
            "printed_page_label": chunk.printed_page_label,
            "rank": hit.rank,
            "reading_inventory_id": chunk.reading_inventory_id,
            "reading_projection_result_id": chunk.reading_projection_result_id,
            "score_hex": hit.score.hex(),
            "source_evidence_id": chunk.source_evidence_id,
            "source_id": chunk.source_id,
            "source_page_id": chunk.source_page_id,
            "source_result_id": chunk.source_result_id,
            "style": chunk.style.value,
            "text_sha256": chunk.text_sha256,
            "text_utf8_bytes": chunk.text_utf8_bytes,
        }
        if frozenset(locator) != _HIT_KEYS:
            raise AdmissionRetrievalError
        locators.append(locator)
    return locators


def admission_record(
    *,
    arguments: AdmissionArguments,
    database: Database[MongoDocument],
    projector: MongoPageProjectionLexicalProjector,
    before: MongoPageProjectionLexicalActiveSnapshot,
    after: MongoPageProjectionLexicalActiveSnapshot,
    document: LoadedDocument,
    plan: UnionPlan,
    replay_generation: PageProjectionLexicalGeneration,
) -> dict[str, object]:
    """Validate replay/retrieval and build one strict admission record."""

    if after.generation != plan.generation:
        raise AdmissionStateError
    after_chunks = active_chunks(projector=projector, snapshot=after)
    before_by_id = {value.chunk_id: value for value in plan.active_chunks}
    after_by_id = {value.chunk_id: value for value in after_chunks}
    if any(
        after_by_id.get(key) != value for key, value in before_by_id.items()
    ):
        raise AdmissionStateError
    if len(after_by_id) != len(plan.union_chunks):
        raise AdmissionStateError
    request = PageProjectionLexicalSearchRequest(
        query=arguments.smoke_query,
        limit=arguments.smoke_limit,
        maximum_candidate_postings=100_000,
    )
    retriever = MongoPageProjectionLexicalRetriever(
        database=database,
        storage_target_id=STORAGE_TARGET_ID,
    )
    retrieval = retriever.search(request=request)
    replay_retrieval = retriever.search(request=request)
    if retrieval != replay_retrieval or not retrieval.hits:
        raise AdmissionRetrievalError
    locators = _hit_locators(
        projector=projector,
        generation=plan.generation,
        hits=retrieval.hits,
    )
    target_locators = tuple(
        value
        for value in locators
        if value["page_projection_result_id"]
        == arguments.page_projection_result_id
    )
    if not target_locators or any(
        not arguments.physical_page_index_first
        <= cast(int, value["physical_page_index"])
        <= arguments.physical_page_index_last
        for value in target_locators
    ):
        raise AdmissionRetrievalError
    validated_after = projector.active_snapshot()
    if validated_after != after:
        raise AdmissionCASError
    if before.generation_id == plan.generation.generation_id:
        disposition = "replayed-identical"
        expected_revision = before.pointer_revision
        pointer_changed = False
    else:
        disposition = "activated"
        expected_revision = (
            1
            if before.pointer_revision is None
            else before.pointer_revision + 1
        )
        pointer_changed = True
    if validated_after.pointer_revision != expected_revision:
        raise AdmissionCASError
    record: dict[str, object] = {
        "active_generation_id_after": validated_after.generation_id,
        "active_generation_id_before": before.generation_id,
        "active_pointer_revision_after": validated_after.pointer_revision,
        "active_pointer_revision_before": before.pointer_revision,
        "active_state_before": ABSENT
        if before.generation is None
        else "present",
        "added_chunk_count": plan.added_chunk_count,
        "admission_result_id": "",
        "capability_id": CAPABILITY_ID,
        "chunk_inventory_id": document.chunk_inventory_id,
        "chunk_selection_id": document.chunk_selection_id,
        "chunking_result_id": document.chunking_result_id,
        "corpus_id": plan.generation.corpus_id,
        "database_name": DATABASE_NAME,
        "disposition": disposition,
        "generation_id": plan.generation.generation_id,
        "hit_locators": locators,
        "index_id": plan.generation.index_id,
        "load_result_id": document.load_result_id,
        "overlapping_chunk_count": plan.overlapping_chunk_count,
        "page_projection_result_id": arguments.page_projection_result_id,
        "phase": "admission",
        "physical_page_index_first": document.physical_page_index_first,
        "physical_page_index_last": document.physical_page_index_last,
        "pointer_changed": pointer_changed,
        "posting_count": plan.generation.posting_count,
        "preserved_chunk_count": len(plan.active_chunks),
        "projection_chunk_counts_after": projection_counts(after_chunks),
        "projection_chunk_counts_before": projection_counts(plan.active_chunks),
        "publication_id": arguments.publication_id,
        "replay_generation_id": replay_generation.generation_id,
        "replay_pointer_revision": validated_after.pointer_revision,
        "retrieval_replay_result_id": replay_retrieval.result_id,
        "retrieval_result_id": retrieval.result_id,
        "schema_id": projector.SCHEMA_ID,
        "smoke_query_request_id": request.request_id,
        "status": "admitted",
        "storage_target_id": STORAGE_TARGET_ID,
        "target_chunk_count": len(document.chunks),
        "term_count": plan.generation.term_count,
        "tokenizer_id": projector._tokenizer.tokenizer_id,
        "total_document_length": plan.generation.total_document_length,
        "union_chunk_count": plan.generation.chunk_count,
        "union_chunk_manifest_sha256": plan.generation.chunk_manifest_sha256,
    }
    record["admission_result_id"] = _identity(
        prefix="page-projection-lexical-admission-result",
        material={
            key: value
            for key, value in record.items()
            if key != "admission_result_id"
        },
    )
    validate_success_record(record=record, phase="admission")
    return record


def validate_success_record(*, record: dict[str, object], phase: str) -> None:
    """Fail closed unless a success record matches its exact safe schema."""

    expected = (
        _PRELIGHT_SUCCESS_KEYS
        if phase == "read-only-preflight"
        else _ADMISSION_SUCCESS_KEYS
        if phase == "admission"
        else frozenset()
    )
    if frozenset(record) != expected:
        raise AdmissionOutputError
    if phase == "read-only-preflight":
        if record.get("status") != "verified":
            raise AdmissionOutputError
    elif record.get("status") != "admitted":
        raise AdmissionOutputError
    for key in (
        "active_projection_chunk_counts",
        "projection_chunk_counts_before",
        "projection_chunk_counts_after",
    ):
        if key not in record:
            continue
        values = record[key]
        if type(values) is not list or len(values) > MAXIMUM_PROJECTION_COUNT:
            raise AdmissionOutputError
        for value in values:
            if (
                type(value) is not dict
                or frozenset(value)
                != {"chunk_count", "page_projection_result_id"}
                or type(value["chunk_count"]) is not int
                or value["chunk_count"] < 1
                or type(value["page_projection_result_id"]) is not str
            ):
                raise AdmissionOutputError
    if "hit_locators" in record:
        hits = record["hit_locators"]
        if type(hits) is not list or not hits or len(hits) > 20:
            raise AdmissionOutputError
        if any(
            type(value) is not dict or frozenset(value) != _HIT_KEYS
            for value in hits
        ):
            raise AdmissionOutputError


def emit_record(
    *, record: dict[str, object], expected_keys: frozenset[str]
) -> None:
    """Emit one canonical bounded JSON line after exact key validation."""

    if frozenset(record) != expected_keys:
        raise AdmissionOutputError
    encoded = json.dumps(
        record,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8", errors="strict")
    if len(encoded) + 1 > MAXIMUM_OUTPUT_BYTES:
        raise AdmissionOutputError
    sys.stdout.buffer.write(encoded + b"\n")
    sys.stdout.buffer.flush()


def emit_success(*, record: dict[str, object], phase: str) -> None:
    """Validate and emit one safe preflight or admission success record."""

    validate_success_record(record=record, phase=phase)
    emit_record(
        record=record,
        expected_keys=(
            _PRELIGHT_SUCCESS_KEYS
            if phase == "read-only-preflight"
            else _ADMISSION_SUCCESS_KEYS
        ),
    )


def emit_failure(*, exit_code: int, category: str, phase: str) -> int:
    """Emit one fixed redacted failure record and return its exit code."""

    emit_record(
        record={
            "category": category,
            "exit_code": exit_code,
            "phase": phase,
            "status": "failed",
        },
        expected_keys=_FAILURE_KEYS,
    )
    return exit_code


def run_preflight(
    *, arguments: AdmissionArguments, connection_uri: str
) -> dict[str, object]:
    """Execute the complete read-only load, union, and Mongo preflight."""

    document = load_document(arguments=arguments)
    client = create_client(connection_uri=connection_uri)
    try:
        database = require_database(client=client)
        projector = MongoPageProjectionLexicalProjector(
            database=database,
            storage_target_id=STORAGE_TARGET_ID,
        )
        verify_required_indexes(projector=projector)
        snapshot = projector.active_snapshot()
        plan = union_plan(
            projector=projector,
            snapshot=snapshot,
            document=document,
        )
        if projector.active_snapshot() != snapshot:
            raise AdmissionStateError
        return preflight_record(
            projector=projector,
            snapshot=snapshot,
            document=document,
            plan=plan,
            publication_id=arguments.publication_id,
            enrichment_result_id=arguments.enrichment_result_id,
        )
    finally:
        client.close()


def run_admission(
    *, arguments: AdmissionArguments, connection_uri: str
) -> dict[str, object]:
    """Execute one exact union stage, revision-CAS activation, and replay."""

    document = load_document(arguments=arguments)
    client = create_client(connection_uri=connection_uri)
    try:
        database = require_database(client=client)
        projector = MongoPageProjectionLexicalProjector(
            database=database,
            storage_target_id=STORAGE_TARGET_ID,
        )
        verify_required_indexes(projector=projector)
        before = projector.active_snapshot()
        if (
            before.generation_id != arguments.expected_active_generation_id
            or before.pointer_revision
            != arguments.expected_active_pointer_revision
        ):
            raise AdmissionCASError
        plan = union_plan(
            projector=projector,
            snapshot=before,
            document=document,
        )
        if (
            plan.generation.generation_id
            != arguments.expected_union_generation_id
            or plan.generation.chunk_manifest_sha256
            != arguments.expected_union_chunk_manifest_sha256
            or plan.generation.chunk_count
            != arguments.expected_union_chunk_count
        ):
            raise AdmissionInventoryError
        # Reobserve the exact generation/revision immediately before any stage
        # writes. The later activation binds the same retained observation.
        second_observation = projector.active_snapshot()
        if second_observation != before:
            raise AdmissionCASError
        staged = projector.stage(chunks=plan.union_chunks)
        if staged != plan.generation:
            raise AdmissionInventoryError
        if before.generation_id == staged.generation_id:
            after = projector.active_snapshot()
            if after != before:
                raise AdmissionCASError
        else:
            try:
                projector.activate(
                    generation=staged,
                    expected_active_generation_id=before.generation_id,
                    expected_active_pointer_revision=before.pointer_revision,
                )
            except MongoPageProjectionLexicalError as error:
                raise AdmissionCASError from error
            after = projector.active_snapshot()
        replay_generation = projector.stage(
            chunks=tuple(reversed(plan.union_chunks))
        )
        replay_snapshot = projector.active_snapshot()
        if replay_generation != staged or replay_snapshot != after:
            raise AdmissionStateError
        return admission_record(
            arguments=arguments,
            database=database,
            projector=projector,
            before=before,
            after=after,
            document=document,
            plan=plan,
            replay_generation=replay_generation,
        )
    finally:
        client.close()


def has_driver_cause(*, error: BaseException) -> bool:
    """Return whether an exception chain contains a Mongo driver failure."""

    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, PyMongoError):
            return True
        current = current.__cause__ or current.__context__
    return False

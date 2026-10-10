"""Deterministic Search-owned chunks from exact page projections."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar

from projectkoios.base import (
    DataObjectActionizer,
    DataObjectActionRequest,
    DataObjectActionResult,
    DataObjectModel,
)
from projectkoios.ingestion.page.projection.result import PageProjectionResult

__all__: tuple[str, ...] = (
    "PageProjectionChunk",
    "PageProjectionChunkInventory",
    "PageProjectionChunkStyle",
    "PageProjectionChunker",
    "PageProjectionChunkingRequest",
    "PageProjectionChunkingResult",
)


class _PageProjectionChunkingImplementation:
    """Own the fixed implementation identity without circular references."""

    ID: ClassVar[str] = "page-projection-chunker"
    VERSION: ClassVar[str] = "1.0"


class _PageProjectionChunkingValidation:
    """Validate values shared by the chunking contract family."""

    MAXIMUM_IDENTITY_BYTES: ClassVar[int] = 1_024
    MAXIMUM_TEXT_BYTES: ClassVar[int] = 262_144

    @classmethod
    def require_identity(cls, *, value: object, label: str) -> str:
        return cls.require_text(
            value=value,
            label=label,
            maximum_bytes=cls.MAXIMUM_IDENTITY_BYTES,
        )

    @staticmethod
    def require_nonnegative_int(*, value: object, label: str) -> int:
        if type(value) is not int or value < 0:
            raise ValueError(f"{label} must be a nonnegative built-in integer")
        return value

    @staticmethod
    def require_text(
        *,
        value: object,
        label: str,
        maximum_bytes: int,
    ) -> str:
        if type(value) is not str or not value:
            raise ValueError(f"{label} must be a nonempty string")
        try:
            encoded = value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as error:
            raise ValueError(f"{label} must be valid UTF-8") from error
        if len(encoded) > maximum_bytes:
            raise ValueError(f"{label} exceeds its byte limit")
        return value


class _PageProjectionChunkingIdentity:
    """Derive bounded identities shared by the chunking contract family."""

    @staticmethod
    def derive(*, prefix: str, material: dict[str, object]) -> str:
        encoded = json.dumps(
            material,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8", errors="strict")
        return f"{prefix}:sha256:{hashlib.sha256(encoded).hexdigest()}"


class PageProjectionChunkStyle(StrEnum):
    """Preserve the admitted page-projection text style."""

    PARAGRAPH = "paragraph"
    HEADING = "heading"
    FIGURE_CAPTION = "figure_caption"


@dataclass(frozen=True, slots=True, kw_only=True)
class PageProjectionChunk(DataObjectModel):
    """Bind one exact projected block to source-local citation provenance."""

    CONTRACT_VERSION: ClassVar[str] = "1.0"
    POLICY_ID: ClassVar[str] = "page-projection-block-local"
    POLICY_VERSION: ClassVar[str] = "1.0"
    PROCESSOR_ID: ClassVar[str] = _PageProjectionChunkingImplementation.ID
    PROCESSOR_VERSION: ClassVar[str] = (
        _PageProjectionChunkingImplementation.VERSION
    )
    MAXIMUM_IDENTITY_BYTES: ClassVar[int] = (
        _PageProjectionChunkingValidation.MAXIMUM_IDENTITY_BYTES
    )
    MAXIMUM_TEXT_BYTES: ClassVar[int] = (
        _PageProjectionChunkingValidation.MAXIMUM_TEXT_BYTES
    )

    page_projection_result_id: str
    source_id: str
    document_id: str
    source_result_id: str
    artifact_verification_result_id: str
    reading_projection_result_id: str
    reading_inventory_id: str
    page_projection_page_id: str
    source_page_id: str
    page_location_id: str
    physical_page_index: int
    printed_page_label: str | None
    page_projection_block_id: str
    source_evidence_id: str
    order_index: int
    style: PageProjectionChunkStyle
    text: str
    text_sha256: str = field(init=False)
    text_utf8_bytes: int = field(init=False)
    chunk_id: str = field(init=False)

    def __post_init__(self) -> None:
        for label, value in (
            ("page projection result ID", self.page_projection_result_id),
            ("source ID", self.source_id),
            ("document ID", self.document_id),
            ("source result ID", self.source_result_id),
            (
                "artifact verification result ID",
                self.artifact_verification_result_id,
            ),
            ("reading projection result ID", self.reading_projection_result_id),
            ("reading inventory ID", self.reading_inventory_id),
            ("page projection page ID", self.page_projection_page_id),
            ("source page ID", self.source_page_id),
            ("page location ID", self.page_location_id),
            ("page projection block ID", self.page_projection_block_id),
            ("source evidence ID", self.source_evidence_id),
        ):
            _PageProjectionChunkingValidation.require_identity(
                value=value, label=label
            )
        _PageProjectionChunkingValidation.require_nonnegative_int(
            value=self.physical_page_index,
            label="physical page index",
        )
        _PageProjectionChunkingValidation.require_nonnegative_int(
            value=self.order_index,
            label="block order index",
        )
        if self.printed_page_label is not None:
            _PageProjectionChunkingValidation.require_text(
                value=self.printed_page_label,
                label="printed page label",
                maximum_bytes=self.MAXIMUM_IDENTITY_BYTES,
            )
        if not isinstance(self.style, PageProjectionChunkStyle):
            raise TypeError("style must be PageProjectionChunkStyle")
        text = _PageProjectionChunkingValidation.require_text(
            value=self.text,
            label="chunk text",
            maximum_bytes=self.MAXIMUM_TEXT_BYTES,
        )
        encoded = text.encode("utf-8", errors="strict")
        text_sha256 = hashlib.sha256(encoded).hexdigest()
        object.__setattr__(self, "text_sha256", text_sha256)
        object.__setattr__(self, "text_utf8_bytes", len(encoded))
        object.__setattr__(
            self,
            "chunk_id",
            _PageProjectionChunkingIdentity.derive(
                prefix="page-projection-chunk",
                material={
                    "contract_version": self.CONTRACT_VERSION,
                    "order_index": self.order_index,
                    "page_location_id": self.page_location_id,
                    "page_projection_block_id": (self.page_projection_block_id),
                    "physical_page_index": self.physical_page_index,
                    "policy_id": self.POLICY_ID,
                    "policy_version": self.POLICY_VERSION,
                    "printed_page_label": self.printed_page_label,
                    "processor_id": self.PROCESSOR_ID,
                    "processor_version": self.PROCESSOR_VERSION,
                    "source_evidence_id": self.source_evidence_id,
                    "source_id": self.source_id,
                    "source_page_id": self.source_page_id,
                    "style": self.style.value,
                    "text_sha256": text_sha256,
                    "text_utf8_bytes": len(encoded),
                    "type": "projectkoios.search.page-projection-chunk",
                },
            ),
        )

    @property
    def physical_page_number(self) -> int:
        """Return the positive physical citation number."""

        return self.physical_page_index + 1


@dataclass(frozen=True, slots=True, init=False)
class PageProjectionChunkInventory(DataObjectModel):
    """Own the ordered complete chunk derivation for one projection result."""

    CONTRACT_VERSION: ClassVar[str] = "1.0"
    MAXIMUM_CHUNKS: ClassVar[int] = 1_000_000

    page_projection_result_id: str
    _chunks: tuple[PageProjectionChunk, ...] = field(repr=True)
    text_utf8_bytes: int
    inventory_id: str

    def __init__(
        self,
        *,
        page_projection_result_id: str,
        chunks: tuple[PageProjectionChunk, ...],
    ) -> None:
        _PageProjectionChunkingValidation.require_identity(
            value=page_projection_result_id,
            label="page projection result ID",
        )
        if type(chunks) is not tuple:
            raise TypeError("chunks must be an immutable tuple")
        if len(chunks) > self.MAXIMUM_CHUNKS:
            raise ValueError("chunk inventory exceeds its count limit")
        if any(type(value) is not PageProjectionChunk for value in chunks):
            raise TypeError("chunk inventory requires exact chunks")
        if any(
            value.page_projection_result_id != page_projection_result_id
            for value in chunks
        ):
            raise ValueError("chunks must bind the inventory projection result")
        chunk_ids = tuple(value.chunk_id for value in chunks)
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("chunk identities must be unique")
        order = tuple(
            (value.physical_page_index, value.order_index) for value in chunks
        )
        if order != tuple(sorted(order)) or len(order) != len(set(order)):
            raise ValueError("chunks must have unique canonical source order")
        object.__setattr__(
            self,
            "page_projection_result_id",
            page_projection_result_id,
        )
        object.__setattr__(self, "_chunks", chunks)
        object.__setattr__(
            self,
            "text_utf8_bytes",
            sum(value.text_utf8_bytes for value in chunks),
        )
        object.__setattr__(
            self,
            "inventory_id",
            self._identity(
                page_projection_result_id=page_projection_result_id,
                chunk_ids=chunk_ids,
            ),
        )

    def __bool__(self) -> bool:
        return bool(self._chunks)

    def __iter__(self) -> Iterator[PageProjectionChunk]:
        return iter(self._chunks)

    def __len__(self) -> int:
        return len(self._chunks)

    @classmethod
    def from_projection_result(
        cls,
        *,
        projection_result: PageProjectionResult,
    ) -> PageProjectionChunkInventory:
        """Derive exactly one Search chunk from each projected text block."""

        PageProjectionChunkingRequest.require_fresh_projection_result(
            projection_result=projection_result
        )
        chunks: list[PageProjectionChunk] = []
        for page in projection_result.pages:
            for block in page.blocks:
                try:
                    style = PageProjectionChunkStyle(block.style.value)
                except (AttributeError, ValueError) as error:
                    raise ValueError(
                        "page projection block has an unsupported style"
                    ) from error
                chunks.append(
                    PageProjectionChunk(
                        page_projection_result_id=projection_result.result_id,
                        source_id=projection_result.source_id.value,
                        document_id=projection_result.document_id.value,
                        source_result_id=projection_result.source_result_id,
                        artifact_verification_result_id=(
                            projection_result.artifact_verification_result_id
                        ),
                        reading_projection_result_id=(
                            projection_result.projection_result_id.value
                        ),
                        reading_inventory_id=(
                            projection_result.reading_inventory_id.value
                        ),
                        page_projection_page_id=page.page_id,
                        source_page_id=page.source_page_id.value,
                        page_location_id=page.page_location.location_id.value,
                        physical_page_index=page.physical_page_index,
                        printed_page_label=page.printed_page_label,
                        page_projection_block_id=block.block_id,
                        source_evidence_id=block.source_id.value,
                        order_index=block.order_index,
                        style=style,
                        text=block.text,
                    )
                )
        return cls(
            page_projection_result_id=projection_result.result_id,
            chunks=tuple(chunks),
        )

    @classmethod
    def _identity(
        cls,
        *,
        page_projection_result_id: str,
        chunk_ids: tuple[str, ...],
    ) -> str:
        digest = hashlib.sha256()
        digest.update(
            cls._framed(
                value=b"projectkoios.search.page-projection-chunk-inventory"
            )
        )
        digest.update(cls._framed(value=cls.CONTRACT_VERSION.encode("ascii")))
        digest.update(
            cls._framed(
                value=page_projection_result_id.encode("utf-8", errors="strict")
            )
        )
        for chunk_id in chunk_ids:
            digest.update(
                cls._framed(value=chunk_id.encode("ascii", errors="strict"))
            )
        return f"page-projection-chunk-inventory:sha256:{digest.hexdigest()}"

    @staticmethod
    def _framed(*, value: bytes) -> bytes:
        return len(value).to_bytes(8, byteorder="big", signed=False) + value


@dataclass(frozen=True, slots=True, kw_only=True)
class PageProjectionChunkingRequest(DataObjectActionRequest):
    """Request the fixed block-local derivation of one exact projection."""

    CONTRACT_NAME: ClassVar[str] = "page-projection-chunking-request"
    CONTRACT_VERSION: ClassVar[str] = "1.0"
    POLICY_ID: ClassVar[str] = PageProjectionChunk.POLICY_ID
    POLICY_VERSION: ClassVar[str] = PageProjectionChunk.POLICY_VERSION

    projection_result: PageProjectionResult
    request_id: str = field(init=False)

    def __post_init__(self) -> None:
        self.require_fresh_projection_result(
            projection_result=self.projection_result
        )
        object.__setattr__(
            self,
            "request_id",
            _PageProjectionChunkingIdentity.derive(
                prefix="page-projection-chunking-request",
                material={
                    "contract_version": self.CONTRACT_VERSION,
                    "page_projection_result_id": (
                        self.projection_result.result_id
                    ),
                    "policy_id": self.POLICY_ID,
                    "policy_version": self.POLICY_VERSION,
                    "type": (
                        "projectkoios.search.page-projection-chunking-request"
                    ),
                },
            ),
        )

    @staticmethod
    def require_fresh_projection_result(
        *,
        projection_result: PageProjectionResult,
    ) -> None:
        """Require one exact fresh current-schema Ingestion leaf result."""

        if type(projection_result) is not PageProjectionResult:
            raise TypeError("projection_result must be PageProjectionResult")
        try:
            fresh = PageProjectionResult(
                request=projection_result.request,
                pages=projection_result.pages,
                limitations=projection_result.limitations,
                reading_evidence_limitations=(
                    projection_result.reading_evidence_limitations
                ),
                processor_id=projection_result.processor_id,
                processor_version=projection_result.processor_version,
            )
        except (TypeError, ValueError) as error:
            raise ValueError("projection_result is stale or invalid") from error
        if fresh != projection_result:
            raise ValueError("projection_result identity is stale")

    @classmethod
    def require_fresh_request(
        cls,
        *,
        request: PageProjectionChunkingRequest,
    ) -> None:
        """Reject post-construction changes to the request or source result."""

        if type(request) is not cls:
            raise TypeError("request must be PageProjectionChunkingRequest")
        try:
            fresh = cls(projection_result=request.projection_result)
        except (TypeError, ValueError) as error:
            raise ValueError("chunking request is stale or invalid") from error
        if fresh != request:
            raise ValueError("chunking request identity is stale")


@dataclass(frozen=True, slots=True, kw_only=True)
class PageProjectionChunkingResult(DataObjectActionResult):
    """Bind one exact request to its complete deterministic chunk inventory."""

    CONTRACT_NAME: ClassVar[str] = "page-projection-chunking-result"
    CONTRACT_VERSION: ClassVar[str] = "1.0"

    request: PageProjectionChunkingRequest
    chunks: PageProjectionChunkInventory
    chunker_implementation_id: str
    chunker_implementation_version: str
    result_id: str = field(init=False)

    def __post_init__(self) -> None:
        PageProjectionChunkingRequest.require_fresh_request(
            request=self.request
        )
        if type(self.chunks) is not PageProjectionChunkInventory:
            raise TypeError("chunks must be PageProjectionChunkInventory")
        expected = PageProjectionChunkInventory.from_projection_result(
            projection_result=self.request.projection_result
        )
        if self.chunks != expected:
            raise ValueError("chunks differ from deterministic derivation")
        _PageProjectionChunkingValidation.require_identity(
            value=self.chunker_implementation_id,
            label="chunker implementation ID",
        )
        _PageProjectionChunkingValidation.require_identity(
            value=self.chunker_implementation_version,
            label="chunker implementation version",
        )
        if (
            self.chunker_implementation_id
            != PageProjectionChunker.IMPLEMENTATION_ID
            or self.chunker_implementation_version
            != PageProjectionChunker.IMPLEMENTATION_VERSION
        ):
            raise ValueError("chunker implementation identity is unsupported")
        object.__setattr__(
            self,
            "result_id",
            _PageProjectionChunkingIdentity.derive(
                prefix="page-projection-chunking-result",
                material={
                    "chunk_inventory_id": self.chunks.inventory_id,
                    "chunker_implementation_id": (
                        self.chunker_implementation_id
                    ),
                    "chunker_implementation_version": (
                        self.chunker_implementation_version
                    ),
                    "contract_version": self.CONTRACT_VERSION,
                    "request_id": self.request.request_id,
                    "type": (
                        "projectkoios.search.page-projection-chunking-result"
                    ),
                },
            ),
        )


class PageProjectionChunker(
    DataObjectActionizer[
        PageProjectionChunkingRequest,
        PageProjectionChunkingResult,
    ]
):
    """Derive fixed block-local Search chunks without side effects."""

    __slots__ = ()

    IMPLEMENTATION_ID: ClassVar[str] = _PageProjectionChunkingImplementation.ID
    IMPLEMENTATION_VERSION: ClassVar[str] = (
        _PageProjectionChunkingImplementation.VERSION
    )

    def action(
        self,
        *,
        request: PageProjectionChunkingRequest,
    ) -> PageProjectionChunkingResult:
        """Return the complete deterministic chunk derivation."""

        PageProjectionChunkingRequest.require_fresh_request(request=request)
        chunks = PageProjectionChunkInventory.from_projection_result(
            projection_result=request.projection_result
        )
        return PageProjectionChunkingResult(
            request=request,
            chunks=chunks,
            chunker_implementation_id=self.IMPLEMENTATION_ID,
            chunker_implementation_version=self.IMPLEMENTATION_VERSION,
        )

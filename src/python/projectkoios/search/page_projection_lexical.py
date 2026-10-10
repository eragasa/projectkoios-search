"""Backend-neutral lexical contracts for exact page-projection chunks.

The module defines the structural input boundary, deterministic tokenizer,
content identities, immutable generation metadata, and bounded search values
used by persistent lexical adapters. It imports no Ingestion or database code.

Notes
-----
The structural protocol prevents storage adapters from importing the concrete
chunking module, whose exact producer boundary imports Ingestion. Production
composition is responsible for supplying actual ``PageProjectionChunk`` values;
the protocol does not create an alternate data-transfer object.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar, Protocol, runtime_checkable

from projectkoios.base import (
    DataObjectActionRequest,
    DataObjectActionResult,
    DataObjectModel,
)

__all__: tuple[str, ...] = (
    "PageProjectionLexicalChunk",
    "PageProjectionLexicalGeneration",
    "PageProjectionLexicalIdentity",
    "PageProjectionLexicalSearchHit",
    "PageProjectionLexicalSearchRequest",
    "PageProjectionLexicalSearchResult",
    "PageProjectionLexicalTokenizer",
)

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_MAXIMUM_IDENTITY_BYTES = 1_024


def _canonical_identity(*, prefix: str, material: dict[str, object]) -> str:
    """Return a deterministic prefixed SHA-256 identity.

    Parameters
    ----------
    prefix
        Stable identity namespace.
    material
        JSON-compatible identity material.

    Returns
    -------
    str
        Prefixed lowercase SHA-256 identity.
    """

    encoded = json.dumps(
        material,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8", errors="strict")
    return f"{prefix}:sha256:{hashlib.sha256(encoded).hexdigest()}"


def _require_identity(*, value: object, label: str) -> str:
    """Return one exact bounded identity string.

    Parameters
    ----------
    value
        Candidate runtime value.
    label
        Human-readable field name for errors.

    Returns
    -------
    str
        Unchanged validated identity.

    Raises
    ------
    ValueError
        If the identity is empty, not an exact string, invalid UTF-8, or too
        large.
    """

    if type(value) is not str or not value:
        raise ValueError(f"{label} must be a nonempty built-in string")
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise ValueError(f"{label} must be valid UTF-8") from error
    if len(encoded) > _MAXIMUM_IDENTITY_BYTES:
        raise ValueError(f"{label} exceeds its byte limit")
    return value


def _require_count(*, value: object, label: str, maximum: int) -> int:
    """Return one exact nonnegative bounded integer.

    Parameters
    ----------
    value
        Candidate runtime value.
    label
        Human-readable field name for errors.
    maximum
        Inclusive fixed ceiling.

    Returns
    -------
    int
        Unchanged validated count.

    Raises
    ------
    ValueError
        If the value is not an exact nonnegative integer or exceeds the bound.
    """

    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a nonnegative built-in integer")
    if value > maximum:
        raise ValueError(f"{label} exceeds its fixed bound")
    return value


@runtime_checkable
class PageProjectionLexicalChunk(Protocol):
    """Describe exact chunk fields consumed by lexical index projection.

    Notes
    -----
    This read-only protocol is intentionally structural. It introduces no
    constructor, serialization, alternate identity, or compatibility layer.
    """

    @property
    def chunk_id(self) -> str:
        """Return the exact Search chunk identity."""
        ...

    @property
    def page_projection_result_id(self) -> str:
        """Return the exact complete projection-result identity."""
        ...

    @property
    def source_id(self) -> str:
        """Return the stable source identity."""
        ...

    @property
    def document_id(self) -> str:
        """Return the canonical reading-document identity."""
        ...

    @property
    def source_result_id(self) -> str:
        """Return the upstream source-result identity."""
        ...

    @property
    def artifact_verification_result_id(self) -> str:
        """Return the artifact-verification result identity."""
        ...

    @property
    def reading_projection_result_id(self) -> str:
        """Return the reading-projection result identity."""
        ...

    @property
    def reading_inventory_id(self) -> str:
        """Return the reading-inventory identity."""
        ...

    @property
    def page_projection_page_id(self) -> str:
        """Return the projected-page identity."""
        ...

    @property
    def source_page_id(self) -> str:
        """Return the canonical source-page identity."""
        ...

    @property
    def page_location_id(self) -> str:
        """Return the citation-location identity."""
        ...

    @property
    def physical_page_index(self) -> int:
        """Return the zero-based physical page index."""
        ...

    @property
    def physical_page_number(self) -> int:
        """Return the one-based physical page number."""
        ...

    @property
    def printed_page_label(self) -> str | None:
        """Return the optional printed-page label."""
        ...

    @property
    def page_projection_block_id(self) -> str:
        """Return the exact projected-block identity."""
        ...

    @property
    def source_evidence_id(self) -> str:
        """Return the source block-or-caption identity."""
        ...

    @property
    def order_index(self) -> int:
        """Return page-local source order."""
        ...

    @property
    def style(self) -> StrEnum:
        """Return the exact closed chunk style."""
        ...

    @property
    def text(self) -> str:
        """Return exact projected text."""
        ...

    @property
    def text_sha256(self) -> str:
        """Return the exact text digest."""
        ...

    @property
    def text_utf8_bytes(self) -> int:
        """Return the exact text byte length."""
        ...


class PageProjectionLexicalTokenizer:
    """Tokenize exact chunk and query text under fixed versioned rules.

    Attributes
    ----------
    IMPLEMENTATION_ID
        Stable tokenizer implementation identity.
    IMPLEMENTATION_VERSION
        Version of the exact token grammar and normalization.
    TOKENIZER_ID
        Exact authoritative opaque tokenizer identity.
    MAXIMUM_TEXT_BYTES
        Largest accepted strict UTF-8 input.
    TERM_PATTERN
        Fixed Unicode-aware term grammar governed by the tokenizer version.
    """

    __slots__ = ()

    IMPLEMENTATION_ID: ClassVar[str] = (
        "projectkoios.search.page-projection-lexical-tokenizer"
    )
    IMPLEMENTATION_VERSION: ClassVar[str] = "1.0"
    TOKENIZER_ID: ClassVar[str] = (
        "projectkoios.search.page-projection-lexical-tokenizer:1.0"
    )
    MAXIMUM_TEXT_BYTES: ClassVar[int] = 262_144
    TERM_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"[^\W_]+(?:[.-][^\W_]+)*",
        re.UNICODE,
    )

    @property
    def tokenizer_id(self) -> str:
        """Return the exact tokenizer configuration identity.

        Returns
        -------
        str
            Exact authoritative opaque tokenizer identity and version.
        """

        return self.TOKENIZER_ID

    def tokens(self, *, text: str) -> tuple[str, ...]:
        """Return ordered lexical tokens including repetitions.

        Parameters
        ----------
        text
            Exact nonblank text to tokenize.

        Returns
        -------
        tuple[str, ...]
            Unicode-casefolded tokens in source order.

        Raises
        ------
        TypeError
            If ``text`` is not an exact built-in string.
        ValueError
            If ``text`` is blank, invalid UTF-8, or exceeds the byte limit.
        """

        if type(text) is not str:
            raise TypeError("tokenizer text must be a built-in string")
        if not text.strip():
            raise ValueError("tokenizer text must be nonblank")
        try:
            encoded = text.encode("utf-8", errors="strict")
        except UnicodeEncodeError as error:
            raise ValueError("tokenizer text must be valid UTF-8") from error
        if len(encoded) > self.MAXIMUM_TEXT_BYTES:
            raise ValueError("tokenizer text exceeds its byte limit")
        return tuple(
            match.group(0)
            for match in self.TERM_PATTERN.finditer(text.casefold())
        )

    def query_terms(self, *, text: str) -> tuple[str, ...]:
        """Return unique query terms in first-seen order.

        Parameters
        ----------
        text
            Exact nonblank query text.

        Returns
        -------
        tuple[str, ...]
            Deduplicated token sequence.
        """

        return tuple(dict.fromkeys(self.tokens(text=text)))


class PageProjectionLexicalIdentity:
    """Derive backend-neutral corpus and index identities."""

    __slots__ = ()

    @staticmethod
    def chunk_manifest(*, chunk_ids: tuple[str, ...]) -> tuple[str, ...]:
        """Return a unique canonical chunk identity manifest.

        Parameters
        ----------
        chunk_ids
            Exact input chunk identities in arbitrary order.

        Returns
        -------
        tuple[str, ...]
            Identities ordered lexicographically.

        Raises
        ------
        TypeError
            If the manifest is not an immutable tuple.
        ValueError
            If an identity is malformed or duplicated.
        """

        if type(chunk_ids) is not tuple:
            raise TypeError("chunk IDs must be an immutable tuple")
        for value in chunk_ids:
            _require_identity(value=value, label="chunk ID")
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("chunk IDs must be unique")
        return tuple(sorted(chunk_ids))

    @classmethod
    def chunk_manifest_sha256(cls, *, chunk_ids: tuple[str, ...]) -> str:
        """Return the digest of the canonical chunk identity manifest.

        Parameters
        ----------
        chunk_ids
            Exact input chunk identities.

        Returns
        -------
        str
            Lowercase SHA-256 of compact canonical JSON manifest bytes.
        """

        manifest = cls.chunk_manifest(chunk_ids=chunk_ids)
        encoded = json.dumps(
            manifest,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8", errors="strict")
        return hashlib.sha256(encoded).hexdigest()

    @classmethod
    def corpus_id(cls, *, chunk_ids: tuple[str, ...]) -> str:
        """Return identity of one canonical exact chunk corpus.

        Parameters
        ----------
        chunk_ids
            Complete exact chunk identity inventory.

        Returns
        -------
        str
            Backend-neutral corpus identity.
        """

        manifest = cls.chunk_manifest(chunk_ids=chunk_ids)
        return _canonical_identity(
            prefix="page-projection-lexical-corpus",
            material={
                "chunk_ids": manifest,
                "type": "projectkoios.search.page-projection-lexical-corpus",
                "version": "1.0",
            },
        )

    @staticmethod
    def index_id(
        *,
        corpus_id: str,
        tokenizer_id: str,
        schema_id: str,
        bm25_k1: float,
        bm25_b: float,
    ) -> str:
        """Return identity of one corpus and exact lexical configuration.

        Parameters
        ----------
        corpus_id
            Canonical chunk corpus identity.
        tokenizer_id
            Exact tokenizer identity.
        schema_id
            Persistent logical schema identity.
        bm25_k1
            Fixed BM25 term-frequency saturation parameter.
        bm25_b
            Fixed BM25 length-normalization parameter.

        Returns
        -------
        str
            Backend-neutral lexical index identity.
        """

        _require_identity(value=corpus_id, label="corpus ID")
        _require_identity(value=tokenizer_id, label="tokenizer ID")
        _require_identity(value=schema_id, label="schema ID")
        if type(bm25_k1) is not float or not math.isfinite(bm25_k1):
            raise ValueError("BM25 k1 must be a finite built-in float")
        if type(bm25_b) is not float or not math.isfinite(bm25_b):
            raise ValueError("BM25 b must be a finite built-in float")
        return _canonical_identity(
            prefix="page-projection-lexical-index",
            material={
                "bm25_b_hex": bm25_b.hex(),
                "bm25_k1_hex": bm25_k1.hex(),
                "corpus_id": corpus_id,
                "schema_id": schema_id,
                "tokenizer_id": tokenizer_id,
                "type": "projectkoios.search.page-projection-lexical-index",
                "version": "1.0",
            },
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PageProjectionLexicalGeneration(DataObjectModel):
    """Bind one immutable corpus/index generation and exact measures.

    Attributes
    ----------
    corpus_id
        Canonical exact chunk-corpus identity.
    index_id
        Canonical lexical index identity.
    schema_id
        Persistent logical schema identity and version.
    tokenizer_id
        Exact tokenizer configuration identity.
    projector_id
        Fixed projection implementation identity and version.
    chunk_manifest_sha256
        Digest of the complete canonical chunk identity manifest.
    index_manifest_sha256
        Digest of canonical chunk, posting, and statistic document material.
    chunk_count
        Number of stored exact chunks.
    posting_count
        Number of term/chunk posting records.
    term_count
        Number of unique lexical terms.
    total_document_length
        Sum of token counts across chunks.
    generation_id
        Derived immutable generation identity.
    """

    MAXIMUM_COUNT: ClassVar[int] = 1_000_000_000

    corpus_id: str
    index_id: str
    schema_id: str
    tokenizer_id: str
    projector_id: str
    chunk_manifest_sha256: str
    index_manifest_sha256: str
    chunk_count: int
    posting_count: int
    term_count: int
    total_document_length: int
    generation_id: str = field(init=False)

    def __post_init__(self) -> None:
        """Validate immutable values and derive generation identity."""

        for identity, label in (
            (self.corpus_id, "corpus ID"),
            (self.index_id, "index ID"),
            (self.schema_id, "schema ID"),
            (self.tokenizer_id, "tokenizer ID"),
            (self.projector_id, "projector ID"),
        ):
            _require_identity(value=identity, label=label)
        for digest, label in (
            (self.chunk_manifest_sha256, "chunk manifest SHA-256"),
            (self.index_manifest_sha256, "index manifest SHA-256"),
        ):
            if (
                type(digest) is not str
                or _SHA256_PATTERN.fullmatch(digest) is None
            ):
                raise ValueError(
                    f"{label} must be 64 lowercase hexadecimal characters"
                )
        for count, label in (
            (self.chunk_count, "chunk count"),
            (self.posting_count, "posting count"),
            (self.term_count, "term count"),
            (self.total_document_length, "total document length"),
        ):
            _require_count(
                value=count,
                label=label,
                maximum=self.MAXIMUM_COUNT,
            )
        object.__setattr__(
            self,
            "generation_id",
            _canonical_identity(
                prefix="page-projection-lexical-generation",
                material={
                    "chunk_count": self.chunk_count,
                    "chunk_manifest_sha256": self.chunk_manifest_sha256,
                    "corpus_id": self.corpus_id,
                    "index_id": self.index_id,
                    "index_manifest_sha256": self.index_manifest_sha256,
                    "posting_count": self.posting_count,
                    "projector_id": self.projector_id,
                    "schema_id": self.schema_id,
                    "term_count": self.term_count,
                    "tokenizer_id": self.tokenizer_id,
                    "total_document_length": self.total_document_length,
                    "type": (
                        "projectkoios.search.page-projection-lexical-generation"
                    ),
                    "version": "1.0",
                },
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PageProjectionLexicalSearchRequest(DataObjectActionRequest):
    """Represent one bounded query over the active lexical generation.

    Attributes
    ----------
    query
        Exact nonblank query text.
    limit
        Maximum number of ordered hits.
    maximum_candidate_postings
        Maximum posting documents the retriever may score.
    request_id
        Derived identity binding query and applied bounds.
    """

    MAXIMUM_QUERY_CHARACTERS: ClassVar[int] = 2_000
    MAXIMUM_QUERY_TERMS: ClassVar[int] = 256
    MAXIMUM_RESULTS: ClassVar[int] = 100
    MAXIMUM_CANDIDATE_POSTINGS: ClassVar[int] = 100_000

    query: str
    limit: int = 10
    maximum_candidate_postings: int = 100_000
    request_id: str = field(init=False)

    def __post_init__(self) -> None:
        """Validate query and bounds and derive request identity."""

        if (
            type(self.query) is not str
            or not self.query.strip()
            or len(self.query) > self.MAXIMUM_QUERY_CHARACTERS
        ):
            raise ValueError("query must contain 1 to 2000 nonblank characters")
        try:
            self.query.encode("utf-8", errors="strict")
        except UnicodeEncodeError as error:
            raise ValueError("query must be valid UTF-8") from error
        if (
            len(PageProjectionLexicalTokenizer().query_terms(text=self.query))
            > self.MAXIMUM_QUERY_TERMS
        ):
            raise ValueError("query exceeds its fixed lexical term bound")
        if (
            type(self.limit) is not int
            or not 1 <= self.limit <= self.MAXIMUM_RESULTS
        ):
            raise ValueError("result limit must be in [1, 100]")
        if (
            type(self.maximum_candidate_postings) is not int
            or not 1
            <= self.maximum_candidate_postings
            <= self.MAXIMUM_CANDIDATE_POSTINGS
        ):
            raise ValueError("candidate posting bound must be in [1, 100000]")
        object.__setattr__(
            self,
            "request_id",
            _canonical_identity(
                prefix="page-projection-lexical-search-request",
                material={
                    "limit": self.limit,
                    "maximum_candidate_postings": (
                        self.maximum_candidate_postings
                    ),
                    "query": self.query,
                    "type": (
                        "projectkoios.search.page-projection-lexical-search-request"
                    ),
                    "version": "1.0",
                },
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PageProjectionLexicalSearchHit(DataObjectModel):
    """Retain one chunk identity and its deterministic BM25 evidence."""

    chunk_id: str
    score: float
    rank: int
    matched_terms: tuple[str, ...]
    hit_id: str = field(init=False)

    def __post_init__(self) -> None:
        """Validate exact ranking evidence and derive hit identity."""

        _require_identity(value=self.chunk_id, label="chunk ID")
        if type(self.score) is not float or not math.isfinite(self.score):
            raise ValueError("score must be a finite built-in float")
        if self.score <= 0.0:
            raise ValueError("score must be positive")
        if type(self.rank) is not int or self.rank < 1:
            raise ValueError("rank must be a positive built-in integer")
        if type(self.matched_terms) is not tuple or not self.matched_terms:
            raise ValueError("matched terms must be a nonempty immutable tuple")
        if any(
            type(value) is not str or not value for value in self.matched_terms
        ):
            raise ValueError("matched terms must contain nonempty strings")
        if len(self.matched_terms) != len(set(self.matched_terms)):
            raise ValueError("matched terms must be unique")
        object.__setattr__(
            self,
            "hit_id",
            _canonical_identity(
                prefix="page-projection-lexical-search-hit",
                material={
                    "chunk_id": self.chunk_id,
                    "matched_terms": self.matched_terms,
                    "rank": self.rank,
                    "score_hex": self.score.hex(),
                    "type": (
                        "projectkoios.search.page-projection-lexical-search-hit"
                    ),
                    "version": "1.0",
                },
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PageProjectionLexicalSearchResult(DataObjectActionResult):
    """Bind one query to one exact active generation and ordered hit set."""

    request: PageProjectionLexicalSearchRequest
    generation: PageProjectionLexicalGeneration
    retriever_id: str
    normalized_query_terms: tuple[str, ...]
    hits: tuple[PageProjectionLexicalSearchHit, ...]
    result_id: str = field(init=False)

    def __post_init__(self) -> None:
        """Validate deterministic ordering and derive result identity."""

        if type(self.request) is not PageProjectionLexicalSearchRequest:
            raise TypeError(
                "request must be PageProjectionLexicalSearchRequest"
            )
        if type(self.generation) is not PageProjectionLexicalGeneration:
            raise TypeError(
                "generation must be PageProjectionLexicalGeneration"
            )
        _require_identity(value=self.retriever_id, label="retriever ID")
        if type(self.normalized_query_terms) is not tuple:
            raise TypeError("normalized query terms must be an immutable tuple")
        if len(self.normalized_query_terms) != len(
            set(self.normalized_query_terms)
        ):
            raise ValueError("normalized query terms must be unique")
        if any(
            type(value) is not str or not value
            for value in self.normalized_query_terms
        ):
            raise ValueError("normalized query terms must be nonempty strings")
        if self.normalized_query_terms != (
            PageProjectionLexicalTokenizer().query_terms(
                text=self.request.query
            )
        ):
            raise ValueError(
                "normalized query terms differ from the versioned tokenizer"
            )
        if type(self.hits) is not tuple:
            raise TypeError("hits must be an immutable tuple")
        if len(self.hits) > self.request.limit:
            raise ValueError("hits exceed the requested result limit")
        if any(
            type(value) is not PageProjectionLexicalSearchHit
            for value in self.hits
        ):
            raise TypeError(
                "hits must be exact PageProjectionLexicalSearchHit values"
            )
        if len({value.chunk_id for value in self.hits}) != len(self.hits):
            raise ValueError("hit chunk identities must be unique")
        if tuple(value.rank for value in self.hits) != tuple(
            range(1, len(self.hits) + 1)
        ):
            raise ValueError("hit ranks must be contiguous and one-based")
        if self.hits != tuple(
            sorted(self.hits, key=lambda value: (-value.score, value.chunk_id))
        ):
            raise ValueError(
                "hits must use deterministic score and identity order"
            )
        if any(
            value.matched_terms
            != tuple(
                term
                for term in self.normalized_query_terms
                if term in value.matched_terms
            )
            for value in self.hits
        ):
            raise ValueError("hit terms must preserve normalized-query order")
        object.__setattr__(
            self,
            "result_id",
            _canonical_identity(
                prefix="page-projection-lexical-search-result",
                material={
                    "generation_id": self.generation.generation_id,
                    "hit_ids": tuple(value.hit_id for value in self.hits),
                    "normalized_query_terms": self.normalized_query_terms,
                    "request_id": self.request.request_id,
                    "retriever_id": self.retriever_id,
                    "type": (
                        "projectkoios.search.page-projection-lexical-search-result"
                    ),
                    "version": "1.0",
                },
            ),
        )

    @property
    def generation_id(self) -> str:
        """Return the exact searched generation identity."""

        return self.generation.generation_id

    @property
    def corpus_id(self) -> str:
        """Return the exact searched corpus identity."""

        return self.generation.corpus_id

    @property
    def index_id(self) -> str:
        """Return the exact searched lexical index identity."""

        return self.generation.index_id

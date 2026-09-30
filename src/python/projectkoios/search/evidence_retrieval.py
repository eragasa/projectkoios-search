"""Bounded text evidence and deterministic retrieval for authoring."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar

from projectkoios.base import (
    DataObjectActionizer,
    DataObjectActionRequest,
    DataObjectActionResult,
    DataObjectModel,
)

__all__: tuple[str, ...] = (
    "AuthoringCorpusRole",
    "AuthoringPurpose",
    "DeterministicLexicalEvidenceRetriever",
    "EvidenceRetrievalResult",
    "EvidenceItem",
    "EvidenceRetrievalRequest",
    "EvidenceRetrievalOutcome",
    "EvidenceWarning",
    "RankedEvidenceItem",
    "ReferenceIdentityStatus",
)


class AuthoringCorpusRole(StrEnum):
    """Identify the only corpus role admitted by the first authoring slice."""

    REFERENCE_EVIDENCE = "reference_evidence"


class AuthoringPurpose(StrEnum):
    """Identify the bounded purpose supported by the first authoring slice."""

    MANUSCRIPT_AUTHORING = "manuscript_authoring"


class ReferenceIdentityStatus(StrEnum):
    """Preserve candidate versus accepted bibliographic identity status."""

    CANDIDATE = "candidate"
    ACCEPTED = "accepted"


class EvidenceRetrievalOutcome(StrEnum):
    """Represent the closed outcomes of bounded authoring retrieval."""

    EVIDENCE_AVAILABLE = "EVIDENCE_AVAILABLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    INVALID_REQUEST = "INVALID_REQUEST"
    INFRASTRUCTURE_FAILURE = "INFRASTRUCTURE_FAILURE"


@dataclass(frozen=True, slots=True, kw_only=True)
class EvidenceWarning(DataObjectModel):
    """Retain one bounded extraction or transformation warning."""

    MAX_CODE_CHARACTERS: ClassVar[int] = 128
    MAX_DETAIL_CHARACTERS: ClassVar[int] = 1_000

    code: str
    detail: str
    warning_id: str = field(init=False)

    def __post_init__(self) -> None:
        self._validate_text(
            value=self.code,
            label="warning code",
            maximum=self.MAX_CODE_CHARACTERS,
        )
        self._validate_text(
            value=self.detail,
            label="warning detail",
            maximum=self.MAX_DETAIL_CHARACTERS,
        )
        object.__setattr__(
            self,
            "warning_id",
            self.identity_for(code=self.code, detail=self.detail),
        )

    @staticmethod
    def identity_for(*, code: str, detail: str) -> str:
        """Return the deterministic identity for exact warning content."""

        payload: dict[str, str] = {
            "code": code,
            "detail": detail,
            "warning_type": "projectkoios.search.evidence-warning",
        }
        canonical: bytes = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        digest: str = hashlib.sha256(canonical).hexdigest()
        return f"evidence-warning:sha256:{digest}"

    @staticmethod
    def _validate_text(*, value: str, label: str, maximum: int) -> None:
        if (
            not isinstance(value, str)
            or not value.strip()
            or value != value.strip()
            or len(value) > maximum
        ):
            raise ValueError(
                f"{label} must contain 1 to {maximum} trimmed characters"
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class EvidenceItem(DataObjectModel):
    """Represent one immutable text item from an independent reference."""

    MAX_ID_CHARACTERS: ClassVar[int] = 512
    MAX_CITEKEY_CHARACTERS: ClassVar[int] = 256
    MAX_PRINTED_PAGE_LABEL_CHARACTERS: ClassVar[int] = 64
    MAX_SOURCE_SPANS: ClassVar[int] = 32
    MAX_INDEXED_TEXT_CHARACTERS: ClassVar[int] = 20_000
    MAX_RETAINED_TEXT_CHARACTERS: ClassVar[int] = 40_000
    MAX_WARNINGS: ClassVar[int] = 32
    SHA256_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}")

    corpus_role: AuthoringCorpusRole
    bibliographic_work_id: str
    reference_identity_status: ReferenceIdentityStatus
    accepted_citekey: str | None
    source_asset_id: str
    transcript_id: str
    page_id: str
    page_index: int
    printed_page_label: str | None
    block_id: str
    source_span_ids: tuple[str, ...]
    indexed_text: str
    indexed_text_sha256: str
    retained_text: str
    retained_text_sha256: str
    warnings: tuple[EvidenceWarning, ...]
    evidence_item_id: str = field(init=False)

    def __post_init__(self) -> None:
        if self.corpus_role is not AuthoringCorpusRole.REFERENCE_EVIDENCE:
            raise ValueError(
                "authoring evidence must use the reference_evidence role"
            )
        if not isinstance(
            self.reference_identity_status,
            ReferenceIdentityStatus,
        ):
            raise ValueError("reference identity status must be explicit")
        self._validate_id(
            value=self.bibliographic_work_id,
            label="bibliographic work ID",
        )
        self._validate_id(
            value=self.source_asset_id,
            label="source asset ID",
        )
        self._validate_id(
            value=self.transcript_id,
            label="transcript ID",
        )
        self._validate_id(
            value=self.page_id,
            label="page ID",
        )
        self._validate_id(
            value=self.block_id,
            label="block ID",
        )
        if (
            isinstance(self.page_index, bool)
            or not isinstance(self.page_index, int)
            or self.page_index < 0
        ):
            raise ValueError("page index must be a nonnegative integer")
        self._validate_optional_text(
            value=self.printed_page_label,
            label="printed page label",
            maximum=self.MAX_PRINTED_PAGE_LABEL_CHARACTERS,
        )
        self._validate_citekey()
        self._validate_source_spans()
        self._validate_evidence_text(
            value=self.indexed_text,
            digest=self.indexed_text_sha256,
            label="indexed text",
            maximum=self.MAX_INDEXED_TEXT_CHARACTERS,
        )
        self._validate_evidence_text(
            value=self.retained_text,
            digest=self.retained_text_sha256,
            label="retained text",
            maximum=self.MAX_RETAINED_TEXT_CHARACTERS,
        )
        self._validate_warnings()
        object.__setattr__(
            self,
            "evidence_item_id",
            self.identity_for(
                corpus_role=self.corpus_role,
                bibliographic_work_id=self.bibliographic_work_id,
                reference_identity_status=self.reference_identity_status,
                accepted_citekey=self.accepted_citekey,
                source_asset_id=self.source_asset_id,
                transcript_id=self.transcript_id,
                page_id=self.page_id,
                page_index=self.page_index,
                printed_page_label=self.printed_page_label,
                block_id=self.block_id,
                source_span_ids=self.source_span_ids,
                indexed_text=self.indexed_text,
                indexed_text_sha256=self.indexed_text_sha256,
                retained_text=self.retained_text,
                retained_text_sha256=self.retained_text_sha256,
                warnings=self.warnings,
            ),
        )

    @staticmethod
    def identity_for(
        *,
        corpus_role: AuthoringCorpusRole,
        bibliographic_work_id: str,
        reference_identity_status: ReferenceIdentityStatus,
        accepted_citekey: str | None,
        source_asset_id: str,
        transcript_id: str,
        page_id: str,
        page_index: int,
        printed_page_label: str | None,
        block_id: str,
        source_span_ids: tuple[str, ...],
        indexed_text: str,
        indexed_text_sha256: str,
        retained_text: str,
        retained_text_sha256: str,
        warnings: tuple[EvidenceWarning, ...],
    ) -> str:
        """Return the deterministic identity of this exact evidence item."""

        payload: dict[str, object] = {
            "accepted_citekey": accepted_citekey,
            "bibliographic_work_id": bibliographic_work_id,
            "block_id": block_id,
            "corpus_role": corpus_role.value,
            "evidence_item_type": "projectkoios.search.evidence-item",
            "indexed_text": indexed_text,
            "indexed_text_sha256": indexed_text_sha256,
            "page_id": page_id,
            "page_index": page_index,
            "printed_page_label": printed_page_label,
            "reference_identity_status": reference_identity_status.value,
            "retained_text": retained_text,
            "retained_text_sha256": retained_text_sha256,
            "source_asset_id": source_asset_id,
            "source_span_ids": source_span_ids,
            "transcript_id": transcript_id,
            "warning_ids": tuple(warning.warning_id for warning in warnings),
        }
        encoded: bytes = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        digest: str = hashlib.sha256(encoded).hexdigest()
        return f"evidence-item:sha256:{digest}"

    @property
    def result_text_characters(self) -> int:
        """Return text characters contributed to a result by this item."""

        return len(self.indexed_text) + len(self.retained_text)

    def _validate_citekey(self) -> None:
        if self.accepted_citekey is None:
            return
        self._validate_optional_text(
            value=self.accepted_citekey,
            label="accepted citekey",
            maximum=self.MAX_CITEKEY_CHARACTERS,
        )
        if (
            self.reference_identity_status
            is not ReferenceIdentityStatus.ACCEPTED
        ):
            raise ValueError(
                "only an accepted reference may carry an accepted citekey"
            )

    def _validate_source_spans(self) -> None:
        if not isinstance(self.source_span_ids, tuple):
            raise ValueError("source span IDs must be an immutable tuple")
        if not 1 <= len(self.source_span_ids) <= self.MAX_SOURCE_SPANS:
            raise ValueError(
                f"evidence requires 1 to {self.MAX_SOURCE_SPANS} source spans"
            )
        for source_span_id in self.source_span_ids:
            self._validate_id(
                value=source_span_id,
                label="source span ID",
            )
        if len(set(self.source_span_ids)) != len(self.source_span_ids):
            raise ValueError("source span IDs must be unique")

    def _validate_warnings(self) -> None:
        if not isinstance(self.warnings, tuple):
            raise ValueError("warnings must be an immutable tuple")
        if len(self.warnings) > self.MAX_WARNINGS:
            raise ValueError(
                f"evidence may contain at most {self.MAX_WARNINGS} warnings"
            )
        if any(
            type(warning) is not EvidenceWarning for warning in self.warnings
        ):
            raise ValueError("evidence warnings must be explicit records")
        if len(set(self.warnings)) != len(self.warnings):
            raise ValueError("evidence warnings must be unique")

    @classmethod
    def _validate_id(cls, *, value: str, label: str) -> None:
        if (
            not isinstance(value, str)
            or not value.strip()
            or value != value.strip()
            or len(value) > cls.MAX_ID_CHARACTERS
        ):
            raise ValueError(
                f"{label} must contain 1 to "
                f"{cls.MAX_ID_CHARACTERS} trimmed characters"
            )

    @staticmethod
    def _validate_optional_text(
        *,
        value: str | None,
        label: str,
        maximum: int,
    ) -> None:
        if value is None:
            return
        if (
            not isinstance(value, str)
            or not value.strip()
            or value != value.strip()
            or len(value) > maximum
        ):
            raise ValueError(
                f"{label} must be absent or contain 1 to {maximum} "
                "trimmed characters"
            )

    @classmethod
    def _validate_evidence_text(
        cls,
        *,
        value: str,
        digest: str,
        label: str,
        maximum: int,
    ) -> None:
        if (
            not isinstance(value, str)
            or not value.strip()
            or len(value) > maximum
        ):
            raise ValueError(f"{label} must contain 1 to {maximum} characters")
        if (
            not isinstance(digest, str)
            or cls.SHA256_PATTERN.fullmatch(digest) is None
        ):
            raise ValueError(f"{label} digest must be lowercase SHA-256")
        expected: str = hashlib.sha256(value.encode("utf-8")).hexdigest()
        if digest != expected:
            raise ValueError(f"{label} digest does not match its text")


@dataclass(frozen=True, slots=True, kw_only=True)
class EvidenceRetrievalRequest(DataObjectActionRequest):
    """Represent one bounded manuscript-authoring lexical query."""

    MAX_QUERY_CHARACTERS: ClassVar[int] = 2_000
    MAX_ID_CHARACTERS: ClassVar[int] = 512
    MAX_WORK_FILTERS: ClassVar[int] = 32
    MAX_RESULTS: ClassVar[int] = 50
    MAX_PER_WORK: ClassVar[int] = 10
    MAX_TOTAL_TEXT_CHARACTERS: ClassVar[int] = 100_000
    MAX_QUERY_TERMS: ClassVar[int] = 256

    purpose: AuthoringPurpose
    query: str
    target_id: str
    bibliographic_work_ids: tuple[str, ...]
    required_bibliographic_work_ids: tuple[str, ...]
    result_limit: int
    per_work_limit: int
    max_total_text_characters: int
    request_id: str = field(init=False)

    def __post_init__(self) -> None:
        if self.purpose is not AuthoringPurpose.MANUSCRIPT_AUTHORING:
            raise ValueError("manuscript_authoring purpose is required")
        self._validate_text(
            value=self.query,
            label="query",
            maximum=self.MAX_QUERY_CHARACTERS,
        )
        self._validate_text(
            value=self.target_id,
            label="target ID",
            maximum=self.MAX_ID_CHARACTERS,
        )
        self._validate_work_ids()
        self._validate_limit(
            value=self.result_limit,
            label="result limit",
            maximum=self.MAX_RESULTS,
        )
        if len(self.required_bibliographic_work_ids) > self.result_limit:
            raise ValueError(
                "result limit cannot be smaller than required work count"
            )
        self._validate_limit(
            value=self.per_work_limit,
            label="per-work limit",
            maximum=self.MAX_PER_WORK,
        )
        if self.per_work_limit > self.result_limit:
            raise ValueError("per-work limit cannot exceed result limit")
        self._validate_limit(
            value=self.max_total_text_characters,
            label="aggregate text limit",
            maximum=self.MAX_TOTAL_TEXT_CHARACTERS,
        )
        object.__setattr__(
            self,
            "request_id",
            self.identity_for(
                purpose=self.purpose,
                query=self.query,
                target_id=self.target_id,
                bibliographic_work_ids=self.bibliographic_work_ids,
                required_bibliographic_work_ids=(
                    self.required_bibliographic_work_ids
                ),
                result_limit=self.result_limit,
                per_work_limit=self.per_work_limit,
                max_total_text_characters=self.max_total_text_characters,
            ),
        )

    @staticmethod
    def identity_for(
        *,
        purpose: AuthoringPurpose,
        query: str,
        target_id: str,
        bibliographic_work_ids: tuple[str, ...],
        required_bibliographic_work_ids: tuple[str, ...],
        result_limit: int,
        per_work_limit: int,
        max_total_text_characters: int,
    ) -> str:
        """Return the deterministic identity for represented request intent."""

        payload: dict[str, object] = {
            "bibliographic_work_ids": bibliographic_work_ids,
            "max_total_text_characters": max_total_text_characters,
            "per_work_limit": per_work_limit,
            "purpose": purpose.value,
            "query": query,
            "request_type": "projectkoios.search.evidence-retrieval-request",
            "required_bibliographic_work_ids": (
                required_bibliographic_work_ids
            ),
            "result_limit": result_limit,
            "target_id": target_id,
        }
        canonical: bytes = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        digest: str = hashlib.sha256(canonical).hexdigest()
        return f"evidence-retrieval-request:sha256:{digest}"

    def _validate_work_ids(self) -> None:
        collections: tuple[tuple[str, tuple[str, ...]], ...] = (
            ("work filters", self.bibliographic_work_ids),
            ("required work IDs", self.required_bibliographic_work_ids),
        )
        for label, values in collections:
            if not isinstance(values, tuple):
                raise ValueError(f"{label} must be an immutable tuple")
            if len(values) > self.MAX_WORK_FILTERS:
                raise ValueError(
                    f"{label} may contain at most {self.MAX_WORK_FILTERS} items"
                )
            for value in values:
                self._validate_text(
                    value=value,
                    label="bibliographic work ID",
                    maximum=self.MAX_ID_CHARACTERS,
                )
            if len(set(values)) != len(values):
                raise ValueError(f"{label} must be unique")
        if self.bibliographic_work_ids and not set(
            self.required_bibliographic_work_ids
        ).issubset(self.bibliographic_work_ids):
            raise ValueError("required works must be included in work filters")

    @staticmethod
    def _validate_text(*, value: str, label: str, maximum: int) -> None:
        if (
            not isinstance(value, str)
            or not value.strip()
            or value != value.strip()
            or len(value) > maximum
        ):
            raise ValueError(
                f"{label} must contain 1 to {maximum} trimmed characters"
            )

    @staticmethod
    def _validate_limit(*, value: int, label: str, maximum: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{label} must be an integer")
        if not 1 <= value <= maximum:
            raise ValueError(f"{label} must be in [1, {maximum}]")


@dataclass(frozen=True, slots=True, kw_only=True)
class RankedEvidenceItem(DataObjectModel):
    """Preserve one selected item and its lexical ranking evidence."""

    item: EvidenceItem
    score: float
    rank: int
    matched_terms: tuple[str, ...]
    tie_key: str
    ranked_evidence_item_id: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.item) is not EvidenceItem:
            raise TypeError("item must be an EvidenceItem")
        if not isinstance(self.score, float) or not math.isfinite(self.score):
            raise ValueError("lexical score must be a finite float")
        if self.score <= 0.0:
            raise ValueError("lexical score must be positive")
        if (
            isinstance(self.rank, bool)
            or not isinstance(self.rank, int)
            or self.rank < 1
        ):
            raise ValueError("rank must be a positive integer")
        if not isinstance(self.matched_terms, tuple) or not self.matched_terms:
            raise ValueError("matched terms must be a nonempty tuple")
        if len(self.matched_terms) > EvidenceRetrievalRequest.MAX_QUERY_TERMS:
            raise ValueError("matched terms exceed the lexical term bound")
        if any(
            not isinstance(term, str) or not term for term in self.matched_terms
        ):
            raise ValueError("matched terms must contain nonempty strings")
        if len(set(self.matched_terms)) != len(self.matched_terms):
            raise ValueError("matched terms must be unique")
        if self.tie_key != self.item.evidence_item_id:
            raise ValueError("tie key must equal the stable evidence item ID")
        object.__setattr__(
            self,
            "ranked_evidence_item_id",
            self.identity_for(
                evidence_item_id=self.item.evidence_item_id,
                score=self.score,
                rank=self.rank,
                matched_terms=self.matched_terms,
                tie_key=self.tie_key,
            ),
        )

    @staticmethod
    def identity_for(
        *,
        evidence_item_id: str,
        score: float,
        rank: int,
        matched_terms: tuple[str, ...],
        tie_key: str,
    ) -> str:
        """Return the deterministic identity for exact ranking evidence."""

        payload: dict[str, object] = {
            "evidence_item_id": evidence_item_id,
            "matched_terms": matched_terms,
            "rank": rank,
            "ranking_type": "projectkoios.search.ranked-evidence-item",
            "score_hex": score.hex(),
            "tie_key": tie_key,
        }
        canonical: bytes = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        digest: str = hashlib.sha256(canonical).hexdigest()
        return f"ranked-evidence-item:sha256:{digest}"


@dataclass(frozen=True, slots=True, kw_only=True)
class EvidenceRetrievalResult(DataObjectActionResult):
    """Represent one bounded deterministic authoring-retrieval result."""

    MAX_WARNINGS: ClassVar[int] = (
        EvidenceRetrievalRequest.MAX_RESULTS * EvidenceItem.MAX_WARNINGS
    )

    request: EvidenceRetrievalRequest
    retriever_implementation_identity: str
    corpus_id: str
    index_id: str
    normalized_query_terms: tuple[str, ...]
    outcome: EvidenceRetrievalOutcome
    evidence: tuple[RankedEvidenceItem, ...]
    candidate_count: int
    omitted_by_per_work_limit: int
    omitted_by_result_limit: int
    omitted_by_aggregate_text_limit: int
    omitted_by_required_work: int
    missing_required_bibliographic_work_ids: tuple[str, ...]
    warnings: tuple[str, ...]
    result_id: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.request) is not EvidenceRetrievalRequest:
            raise TypeError("request must be an EvidenceRetrievalRequest")
        self._validate_id(
            value=self.retriever_implementation_identity,
            label="retriever implementation ID",
        )
        self._validate_id(
            value=self.corpus_id,
            label="corpus ID",
        )
        self._validate_id(
            value=self.index_id,
            label="index ID",
        )
        if not isinstance(self.outcome, EvidenceRetrievalOutcome):
            raise ValueError("result outcome must be explicit")
        self._validate_normalized_terms()
        self._validate_evidence()
        self._validate_omissions()
        self._validate_missing_required_works()
        self._validate_warnings()
        self._validate_outcome()
        object.__setattr__(
            self,
            "result_id",
            self.identity_for(
                request=self.request,
                retriever_implementation_identity=(
                    self.retriever_implementation_identity
                ),
                corpus_id=self.corpus_id,
                index_id=self.index_id,
                normalized_query_terms=self.normalized_query_terms,
                outcome=self.outcome,
                evidence=self.evidence,
                candidate_count=self.candidate_count,
                omitted_by_per_work_limit=(self.omitted_by_per_work_limit),
                omitted_by_result_limit=self.omitted_by_result_limit,
                omitted_by_aggregate_text_limit=(
                    self.omitted_by_aggregate_text_limit
                ),
                omitted_by_required_work=self.omitted_by_required_work,
                missing_required_bibliographic_work_ids=(
                    self.missing_required_bibliographic_work_ids
                ),
                warnings=self.warnings,
            ),
        )

    @staticmethod
    def identity_for(
        *,
        request: EvidenceRetrievalRequest,
        retriever_implementation_identity: str,
        corpus_id: str,
        index_id: str,
        normalized_query_terms: tuple[str, ...],
        outcome: EvidenceRetrievalOutcome,
        evidence: tuple[RankedEvidenceItem, ...],
        candidate_count: int,
        omitted_by_per_work_limit: int,
        omitted_by_result_limit: int,
        omitted_by_aggregate_text_limit: int,
        omitted_by_required_work: int,
        missing_required_bibliographic_work_ids: tuple[str, ...],
        warnings: tuple[str, ...],
    ) -> str:
        """Return the identity binding request, retriever, and exact result."""

        payload: dict[str, object] = {
            "candidate_count": candidate_count,
            "corpus_id": corpus_id,
            "index_id": index_id,
            "missing_required_bibliographic_work_ids": (
                missing_required_bibliographic_work_ids
            ),
            "normalized_query_terms": normalized_query_terms,
            "omitted_by_aggregate_text_limit": (
                omitted_by_aggregate_text_limit
            ),
            "omitted_by_per_work_limit": omitted_by_per_work_limit,
            "omitted_by_required_work": omitted_by_required_work,
            "omitted_by_result_limit": omitted_by_result_limit,
            "outcome": outcome.value,
            "ranked_evidence_item_ids": tuple(
                item.ranked_evidence_item_id for item in evidence
            ),
            "request_id": request.request_id,
            "result_type": "projectkoios.search.evidence-retrieval-result",
            "retriever_implementation_identity": (
                retriever_implementation_identity
            ),
            "warnings": warnings,
        }
        canonical: bytes = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        digest: str = hashlib.sha256(canonical).hexdigest()
        return f"evidence-retrieval-result:sha256:{digest}"

    @property
    def omitted_count(self) -> int:
        """Return the total number of scored candidates not selected."""

        return (
            self.omitted_by_per_work_limit
            + self.omitted_by_result_limit
            + self.omitted_by_aggregate_text_limit
            + self.omitted_by_required_work
        )

    @property
    def selected_text_characters(self) -> int:
        """Return indexed plus retained text characters in selected items."""

        return sum(
            ranked.item.result_text_characters for ranked in self.evidence
        )

    @property
    def truncated(self) -> bool:
        """Report whether an ordinary selection bound omitted candidates."""

        return any(
            (
                self.omitted_by_per_work_limit,
                self.omitted_by_result_limit,
                self.omitted_by_aggregate_text_limit,
            )
        )

    def _validate_normalized_terms(self) -> None:
        if not isinstance(self.normalized_query_terms, tuple):
            raise ValueError(
                "normalized query terms must be an immutable tuple"
            )
        if (
            len(self.normalized_query_terms)
            > EvidenceRetrievalRequest.MAX_QUERY_TERMS
        ):
            raise ValueError("normalized query terms exceed their bound")
        if any(
            not isinstance(term, str) or not term
            for term in self.normalized_query_terms
        ):
            raise ValueError("normalized query terms must be nonempty strings")
        if len(set(self.normalized_query_terms)) != len(
            self.normalized_query_terms
        ):
            raise ValueError("normalized query terms must be unique")

    def _validate_evidence(self) -> None:
        if not isinstance(self.evidence, tuple):
            raise ValueError("result evidence must be an immutable tuple")
        if len(self.evidence) > self.request.result_limit:
            raise ValueError("result exceeds the requested item limit")
        if any(
            type(ranked) is not RankedEvidenceItem for ranked in self.evidence
        ):
            raise ValueError(
                "result evidence entries must be ranked evidence items"
            )
        expected_ranks: tuple[int, ...] = tuple(
            range(1, len(self.evidence) + 1)
        )
        if tuple(ranked.rank for ranked in self.evidence) != expected_ranks:
            raise ValueError("result ranks must be contiguous and one-based")
        ordered: tuple[RankedEvidenceItem, ...] = tuple(
            sorted(
                self.evidence,
                key=lambda ranked: (-ranked.score, ranked.tie_key),
            )
        )
        if self.evidence != ordered:
            raise ValueError("result evidence ordering is not deterministic")
        if any(
            not set(ranked.matched_terms).issubset(self.normalized_query_terms)
            for ranked in self.evidence
        ):
            raise ValueError(
                "matched terms must come from the normalized query"
            )
        if self.request.bibliographic_work_ids and any(
            ranked.item.bibliographic_work_id
            not in self.request.bibliographic_work_ids
            for ranked in self.evidence
        ):
            raise ValueError("result contains evidence outside work filters")
        work_counts: Counter[str] = Counter(
            ranked.item.bibliographic_work_id for ranked in self.evidence
        )
        if any(
            count > self.request.per_work_limit
            for count in work_counts.values()
        ):
            raise ValueError("result exceeds its per-work limit")
        if self.selected_text_characters > (
            self.request.max_total_text_characters
        ):
            raise ValueError("result exceeds its aggregate text limit")

    def _validate_omissions(self) -> None:
        values: tuple[tuple[str, int], ...] = (
            ("candidate count", self.candidate_count),
            ("per-work omission count", self.omitted_by_per_work_limit),
            ("result-limit omission count", self.omitted_by_result_limit),
            (
                "aggregate-text omission count",
                self.omitted_by_aggregate_text_limit,
            ),
            ("required-work omission count", self.omitted_by_required_work),
        )
        for label, value in values:
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(f"{label} must be a nonnegative integer")
        if self.candidate_count != len(self.evidence) + self.omitted_count:
            raise ValueError("candidate and omission counts are inconsistent")

    def _validate_missing_required_works(self) -> None:
        if not isinstance(self.missing_required_bibliographic_work_ids, tuple):
            raise ValueError(
                "missing required works must be an immutable tuple"
            )
        if len(set(self.missing_required_bibliographic_work_ids)) != len(
            self.missing_required_bibliographic_work_ids
        ):
            raise ValueError("missing required works must be unique")
        if not set(self.missing_required_bibliographic_work_ids).issubset(
            self.request.required_bibliographic_work_ids
        ):
            raise ValueError("missing works must be required by the request")

    def _validate_warnings(self) -> None:
        if not isinstance(self.warnings, tuple):
            raise ValueError("result warnings must be an immutable tuple")
        if len(self.warnings) > self.MAX_WARNINGS:
            raise ValueError("result warnings exceed their fixed bound")
        if any(
            not isinstance(warning, str)
            or not warning
            or len(warning) > EvidenceWarning.MAX_CODE_CHARACTERS
            for warning in self.warnings
        ):
            raise ValueError("result warnings must be bounded warning codes")
        if len(set(self.warnings)) != len(self.warnings):
            raise ValueError("result warnings must be unique")

    def _validate_outcome(self) -> None:
        available: bool = (
            self.outcome is EvidenceRetrievalOutcome.EVIDENCE_AVAILABLE
        )
        if available != bool(self.evidence):
            raise ValueError(
                "evidence is present exactly when its outcome is available"
            )
        if available:
            selected_works: set[str] = {
                ranked.item.bibliographic_work_id for ranked in self.evidence
            }
            if not set(self.request.required_bibliographic_work_ids).issubset(
                selected_works
            ):
                raise ValueError("available evidence omits a required work")
            if self.missing_required_bibliographic_work_ids:
                raise ValueError(
                    "available evidence cannot report missing works"
                )
        if self.outcome in {
            EvidenceRetrievalOutcome.INVALID_REQUEST,
            EvidenceRetrievalOutcome.INFRASTRUCTURE_FAILURE,
        }:
            if self.candidate_count != 0 or self.omitted_count != 0:
                raise ValueError("failed retrieval cannot report candidates")
            if not self.warnings:
                raise ValueError("failed retrieval requires a warning code")
        if self.outcome is EvidenceRetrievalOutcome.INSUFFICIENT_EVIDENCE:
            has_mechanical_reason: bool = (
                self.candidate_count == 0
                or bool(self.missing_required_bibliographic_work_ids)
                or self.omitted_by_aggregate_text_limit > 0
            )
            if not has_mechanical_reason:
                raise ValueError(
                    "insufficient evidence requires a mechanical reason"
                )

    @staticmethod
    def _validate_id(*, value: str, label: str) -> None:
        if (
            not isinstance(value, str)
            or not value.strip()
            or value != value.strip()
            or len(value) > EvidenceRetrievalRequest.MAX_ID_CHARACTERS
        ):
            raise ValueError(
                f"{label} must contain 1 to "
                f"{EvidenceRetrievalRequest.MAX_ID_CHARACTERS} "
                "trimmed characters"
            )


class DeterministicLexicalEvidenceRetriever(
    DataObjectActionizer[EvidenceRetrievalRequest, EvidenceRetrievalResult]
):
    """Retrieve bounded reference evidence with deterministic lexical BM25."""

    __slots__ = ("_corpus_id", "_index_id", "_items")

    TERM_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"[^\W_]+(?:[.-][^\W_]+)*",
        re.UNICODE,
    )
    BM25_K1: ClassVar[float] = 1.2
    BM25_B: ClassVar[float] = 0.75
    IMPLEMENTATION_IDENTITY: ClassVar[str] = (
        "projectkoios.search.deterministic-lexical-evidence-retriever"
    )

    def __init__(
        self,
        *,
        corpus_id: str,
        items: tuple[EvidenceItem, ...],
    ) -> None:
        self._validate_id(
            value=corpus_id,
            label="corpus ID",
        )
        if not isinstance(items, tuple):
            raise ValueError("retriever items must be an immutable tuple")
        if any(type(item) is not EvidenceItem for item in items):
            raise TypeError("items must be an EvidenceItem tuple")
        evidence_item_ids: tuple[str, ...] = tuple(
            item.evidence_item_id for item in items
        )
        if len(set(evidence_item_ids)) != len(evidence_item_ids):
            raise ValueError(
                "retriever items must have unique evidence item IDs"
            )
        ordered_items: tuple[EvidenceItem, ...] = tuple(
            sorted(items, key=lambda item: item.evidence_item_id)
        )
        self._corpus_id = corpus_id
        self._items = ordered_items
        self._index_id = self._derive_index_id(
            corpus_id=corpus_id,
            items=ordered_items,
        )

    @property
    def corpus_id(self) -> str:
        """Return the exact admitted-corpus identity."""

        return self._corpus_id

    @property
    def index_id(self) -> str:
        """Return the identity of the corpus and fixed lexical configuration."""

        return self._index_id

    def action(
        self, *, request: EvidenceRetrievalRequest
    ) -> EvidenceRetrievalResult:
        """Return the result of the semantic retrieval method."""

        return self.retrieve(request=request)

    def retrieve(
        self, *, request: EvidenceRetrievalRequest
    ) -> EvidenceRetrievalResult:
        """Retrieve a bounded deterministic evidence result."""

        if type(request) is not EvidenceRetrievalRequest:
            raise TypeError("request must be an EvidenceRetrievalRequest")
        query_terms: tuple[str, ...] = tuple(
            dict.fromkeys(self._terms(text=request.query))
        )
        if not query_terms:
            return self._result(
                request=request,
                query_terms=(),
                outcome=EvidenceRetrievalOutcome.INVALID_REQUEST,
                evidence=(),
                candidate_count=0,
                omitted_by_per_work_limit=0,
                omitted_by_result_limit=0,
                omitted_by_aggregate_text_limit=0,
                omitted_by_required_work=0,
                missing_required_bibliographic_work_ids=(),
                warnings=("QUERY_HAS_NO_LEXICAL_TERMS",),
            )
        if len(query_terms) > EvidenceRetrievalRequest.MAX_QUERY_TERMS:
            return self._result(
                request=request,
                query_terms=query_terms[
                    : EvidenceRetrievalRequest.MAX_QUERY_TERMS
                ],
                outcome=EvidenceRetrievalOutcome.INVALID_REQUEST,
                evidence=(),
                candidate_count=0,
                omitted_by_per_work_limit=0,
                omitted_by_result_limit=0,
                omitted_by_aggregate_text_limit=0,
                omitted_by_required_work=0,
                missing_required_bibliographic_work_ids=(),
                warnings=("QUERY_EXCEEDS_LEXICAL_TERM_LIMIT",),
            )
        scored: tuple[tuple[EvidenceItem, float, tuple[str, ...]], ...] = (
            self._score_candidates(
                request=request,
                query_terms=query_terms,
            )
        )
        missing_required: tuple[str, ...] = self._missing_required_works(
            request=request,
            scored=scored,
        )
        if missing_required:
            return self._result(
                request=request,
                query_terms=query_terms,
                outcome=EvidenceRetrievalOutcome.INSUFFICIENT_EVIDENCE,
                evidence=(),
                candidate_count=len(scored),
                omitted_by_per_work_limit=0,
                omitted_by_result_limit=0,
                omitted_by_aggregate_text_limit=0,
                omitted_by_required_work=len(scored),
                missing_required_bibliographic_work_ids=missing_required,
                warnings=(),
            )
        (
            selected,
            omitted_by_per_work,
            omitted_by_result,
            omitted_by_aggregate,
        ) = self._select_candidates(request=request, scored=scored)
        selected_works: set[str] = {
            item.bibliographic_work_id for item, _, _ in selected
        }
        unselected_required: tuple[str, ...] = tuple(
            bibliographic_work_id
            for bibliographic_work_id in (
                request.required_bibliographic_work_ids
            )
            if bibliographic_work_id not in selected_works
        )
        if unselected_required:
            return self._result(
                request=request,
                query_terms=query_terms,
                outcome=EvidenceRetrievalOutcome.INSUFFICIENT_EVIDENCE,
                evidence=(),
                candidate_count=len(scored),
                omitted_by_per_work_limit=0,
                omitted_by_result_limit=0,
                omitted_by_aggregate_text_limit=0,
                omitted_by_required_work=len(scored),
                missing_required_bibliographic_work_ids=unselected_required,
                warnings=(),
            )
        if not selected:
            return self._result(
                request=request,
                query_terms=query_terms,
                outcome=EvidenceRetrievalOutcome.INSUFFICIENT_EVIDENCE,
                evidence=(),
                candidate_count=len(scored),
                omitted_by_per_work_limit=omitted_by_per_work,
                omitted_by_result_limit=omitted_by_result,
                omitted_by_aggregate_text_limit=omitted_by_aggregate,
                omitted_by_required_work=0,
                missing_required_bibliographic_work_ids=(),
                warnings=(),
            )
        ranked: tuple[RankedEvidenceItem, ...] = tuple(
            RankedEvidenceItem(
                item=item,
                score=score,
                rank=rank,
                matched_terms=matched_terms,
                tie_key=item.evidence_item_id,
            )
            for rank, (item, score, matched_terms) in enumerate(
                selected,
                start=1,
            )
        )
        return self._result(
            request=request,
            query_terms=query_terms,
            outcome=EvidenceRetrievalOutcome.EVIDENCE_AVAILABLE,
            evidence=ranked,
            candidate_count=len(scored),
            omitted_by_per_work_limit=omitted_by_per_work,
            omitted_by_result_limit=omitted_by_result,
            omitted_by_aggregate_text_limit=omitted_by_aggregate,
            omitted_by_required_work=0,
            missing_required_bibliographic_work_ids=(),
            warnings=self._warning_codes(evidence=ranked),
        )

    def _score_candidates(
        self,
        *,
        request: EvidenceRetrievalRequest,
        query_terms: tuple[str, ...],
    ) -> tuple[tuple[EvidenceItem, float, tuple[str, ...]], ...]:
        eligible: tuple[EvidenceItem, ...] = tuple(
            item
            for item in self._items
            if not request.bibliographic_work_ids
            or item.bibliographic_work_id in request.bibliographic_work_ids
        )
        document_terms: dict[str, tuple[str, ...]] = {
            item.evidence_item_id: self._terms(text=item.indexed_text)
            for item in eligible
        }
        average_length: float = (
            sum(len(terms) for terms in document_terms.values())
            / len(document_terms)
            if document_terms
            else 0.0
        )
        document_frequencies: dict[str, int] = {
            term: sum(
                term in document_terms[item.evidence_item_id]
                for item in eligible
            )
            for term in query_terms
        }
        scored: list[tuple[EvidenceItem, float, tuple[str, ...]]] = []
        for item in eligible:
            terms: tuple[str, ...] = document_terms[item.evidence_item_id]
            counts: Counter[str] = Counter(terms)
            score: float = self._bm25_score(
                query_terms=query_terms,
                counts=counts,
                document_length=len(terms),
                document_count=len(eligible),
                document_frequencies=document_frequencies,
                average_document_length=average_length,
            )
            if score <= 0.0:
                continue
            matched_terms: tuple[str, ...] = tuple(
                term for term in query_terms if counts[term] > 0
            )
            scored.append((item, score, matched_terms))
        scored.sort(key=lambda value: (-value[1], value[0].evidence_item_id))
        return tuple(scored)

    @classmethod
    def _bm25_score(
        cls,
        *,
        query_terms: tuple[str, ...],
        counts: Counter[str],
        document_length: int,
        document_count: int,
        document_frequencies: dict[str, int],
        average_document_length: float,
    ) -> float:
        if document_count == 0 or average_document_length == 0.0:
            return 0.0
        score: float = 0.0
        for term in query_terms:
            term_frequency: int = counts[term]
            if term_frequency == 0:
                continue
            document_frequency: int = document_frequencies[term]
            inverse_document_frequency: float = math.log(
                1.0
                + (document_count - document_frequency + 0.5)
                / (document_frequency + 0.5)
            )
            normalization: float = term_frequency + cls.BM25_K1 * (
                1.0
                - cls.BM25_B
                + cls.BM25_B * document_length / average_document_length
            )
            score += inverse_document_frequency * (
                term_frequency * (cls.BM25_K1 + 1.0) / normalization
            )
        return score

    @classmethod
    def _terms(cls, *, text: str) -> tuple[str, ...]:
        return tuple(
            match.group(0)
            for match in cls.TERM_PATTERN.finditer(text.casefold())
        )

    @staticmethod
    def _missing_required_works(
        *,
        request: EvidenceRetrievalRequest,
        scored: tuple[tuple[EvidenceItem, float, tuple[str, ...]], ...],
    ) -> tuple[str, ...]:
        available_works: set[str] = {
            item.bibliographic_work_id for item, _, _ in scored
        }
        return tuple(
            bibliographic_work_id
            for bibliographic_work_id in (
                request.required_bibliographic_work_ids
            )
            if bibliographic_work_id not in available_works
        )

    @staticmethod
    def _select_candidates(
        *,
        request: EvidenceRetrievalRequest,
        scored: tuple[tuple[EvidenceItem, float, tuple[str, ...]], ...],
    ) -> tuple[
        tuple[tuple[EvidenceItem, float, tuple[str, ...]], ...],
        int,
        int,
        int,
    ]:
        selected: list[tuple[EvidenceItem, float, tuple[str, ...]]] = []
        work_counts: Counter[str] = Counter()
        text_characters: int = 0
        omitted_by_per_work: int = 0
        omitted_by_result: int = 0
        omitted_by_aggregate: int = 0
        for candidate in scored:
            item: EvidenceItem = candidate[0]
            if len(selected) >= request.result_limit:
                omitted_by_result += 1
                continue
            if (
                work_counts[item.bibliographic_work_id]
                >= request.per_work_limit
            ):
                omitted_by_per_work += 1
                continue
            candidate_characters: int = item.result_text_characters
            if (
                text_characters + candidate_characters
                > request.max_total_text_characters
            ):
                omitted_by_aggregate += 1
                continue
            selected.append(candidate)
            work_counts[item.bibliographic_work_id] += 1
            text_characters += candidate_characters
        return (
            tuple(selected),
            omitted_by_per_work,
            omitted_by_result,
            omitted_by_aggregate,
        )

    @staticmethod
    def _warning_codes(
        *,
        evidence: tuple[RankedEvidenceItem, ...],
    ) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                warning.code
                for ranked in evidence
                for warning in ranked.item.warnings
            )
        )

    def _result(
        self,
        *,
        request: EvidenceRetrievalRequest,
        query_terms: tuple[str, ...],
        outcome: EvidenceRetrievalOutcome,
        evidence: tuple[RankedEvidenceItem, ...],
        candidate_count: int,
        omitted_by_per_work_limit: int,
        omitted_by_result_limit: int,
        omitted_by_aggregate_text_limit: int,
        omitted_by_required_work: int,
        missing_required_bibliographic_work_ids: tuple[str, ...],
        warnings: tuple[str, ...],
    ) -> EvidenceRetrievalResult:
        return EvidenceRetrievalResult(
            request=request,
            retriever_implementation_identity=self.IMPLEMENTATION_IDENTITY,
            corpus_id=self.corpus_id,
            index_id=self.index_id,
            normalized_query_terms=query_terms,
            outcome=outcome,
            evidence=evidence,
            candidate_count=candidate_count,
            omitted_by_per_work_limit=omitted_by_per_work_limit,
            omitted_by_result_limit=omitted_by_result_limit,
            omitted_by_aggregate_text_limit=(omitted_by_aggregate_text_limit),
            omitted_by_required_work=omitted_by_required_work,
            missing_required_bibliographic_work_ids=(
                missing_required_bibliographic_work_ids
            ),
            warnings=warnings,
        )

    @classmethod
    def _derive_index_id(
        cls,
        *,
        corpus_id: str,
        items: tuple[EvidenceItem, ...],
    ) -> str:
        payload: dict[str, object] = {
            "bm25_b": cls.BM25_B,
            "bm25_k1": cls.BM25_K1,
            "corpus_id": corpus_id,
            "evidence_item_ids": tuple(item.evidence_item_id for item in items),
            "implementation_identity": cls.IMPLEMENTATION_IDENTITY,
            "term_pattern": cls.TERM_PATTERN.pattern,
        }
        encoded: bytes = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        digest: str = hashlib.sha256(encoded).hexdigest()
        return f"authoring-lexical-index:sha256:{digest}"

    @staticmethod
    def _validate_id(*, value: str, label: str) -> None:
        if (
            not isinstance(value, str)
            or not value.strip()
            or value != value.strip()
            or len(value) > EvidenceRetrievalRequest.MAX_ID_CHARACTERS
        ):
            raise ValueError(
                f"{label} must contain 1 to "
                f"{EvidenceRetrievalRequest.MAX_ID_CHARACTERS} "
                "trimmed characters"
            )

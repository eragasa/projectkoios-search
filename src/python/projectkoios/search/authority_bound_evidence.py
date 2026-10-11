"""Accepted-authority admission for production manuscript evidence.

This module is the only production bridge from exact Search page-projection
chunks, the public Ingestion enrichment leaf, and the References-owned Search
authority projection into the existing deterministic authoring evidence family.
The older evidence classes remain usable for prototypes and review contexts;
production retrieval through this module admits only complete replay-current
accepted authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar

from projectkoios.base import (
    DataObjectActionizer,
    DataObjectActionRequest,
    DataObjectActionResult,
    DataObjectModel,
)
from projectkoios.ingestion.page.projection.enrichment.actionizer import (
    PageProjectionEvidenceEnrichmentActionizer,
)
from projectkoios.ingestion.page.projection.enrichment.record import (
    PageProjectionEvidenceEnrichment,
    PageProjectionEvidenceEntry,
    PageProjectionEvidenceUnavailable,
)
from projectkoios.ingestion.page.projection.enrichment.request import (
    PageProjectionEvidenceEnrichmentRequest,
)
from projectkoios.ingestion.page.projection.enrichment.result import (
    PageProjectionEvidenceEnrichmentResult,
)
from projectkoios.references.course_reference_authority import (
    IngestionArtifactAuthorityLink,
    SearchReferenceAuthorityBinding,
    SearchReferenceAuthorityProjection,
)
from projectkoios.search.evidence_retrieval import (
    AuthoringCorpusRole,
    DeterministicLexicalEvidenceRetriever,
    EvidenceCorpus,
    EvidenceItem,
    EvidenceRetrievalRequest,
    EvidenceRetrievalResult,
    ReferenceIdentityStatus,
)
from projectkoios.search.page_projection_chunking import (
    PageProjectionChunk,
    PageProjectionChunker,
    PageProjectionChunkingResult,
)

__all__: tuple[str, ...] = (
    "AuthorityBoundDeterministicLexicalEvidenceRetriever",
    "AuthorityBoundEvidenceAdmission",
    "AuthorityBoundEvidenceAdmissionComposer",
    "AuthorityBoundEvidenceAdmissionError",
    "AuthorityBoundEvidenceAdmissionRequest",
    "AuthorityBoundEvidenceAdmissionResult",
    "AuthorityBoundEvidenceOmission",
    "AuthorityBoundEvidenceOmissionReason",
    "AuthorityBoundEvidenceRetrievalResult",
)

_MAXIMUM_INPUT_CHUNKS = 100_000
_MAXIMUM_IDENTITY_BYTES = 1_024


class AuthorityBoundEvidenceAdmissionError(ValueError):
    """Report stale, malformed, or mutually inconsistent admission input."""


class AuthorityBoundEvidenceOmissionReason(StrEnum):
    """Explain why one exact chunk was not admitted to production evidence."""

    MISSING_INGESTION_ENRICHMENT = "missing_ingestion_enrichment"
    ENRICHMENT_UNAVAILABLE = "enrichment_unavailable"
    MISSING_REFERENCE_AUTHORITY = "missing_reference_authority"
    INCONSISTENT_BINDING = "inconsistent_binding"
    OVER_LIMIT = "over_limit"


def _identity(*, namespace: str, material: dict[str, object]) -> str:
    encoded = json.dumps(
        material,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8", errors="strict")
    return f"{namespace}:sha256:{hashlib.sha256(encoded).hexdigest()}"


def _require_identity(value: object, *, label: str) -> str:
    if type(value) is not str or not value:
        raise AuthorityBoundEvidenceAdmissionError(
            f"{label} must be a nonempty built-in string"
        )
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise AuthorityBoundEvidenceAdmissionError(
            f"{label} must be valid UTF-8"
        ) from error
    if len(encoded) > _MAXIMUM_IDENTITY_BYTES:
        raise AuthorityBoundEvidenceAdmissionError(
            f"{label} exceeds its byte limit"
        )
    return value


def _fresh_chunking_result(
    value: PageProjectionChunkingResult,
) -> PageProjectionChunkingResult:
    if type(value) is not PageProjectionChunkingResult:
        raise TypeError("chunking_result must be PageProjectionChunkingResult")
    try:
        fresh = PageProjectionChunker().action(request=value.request)
    except (TypeError, ValueError) as error:
        raise AuthorityBoundEvidenceAdmissionError(
            "chunking result is stale or malformed"
        ) from error
    if fresh != value:
        raise AuthorityBoundEvidenceAdmissionError(
            "chunking result differs from deterministic derivation"
        )
    return fresh


def _fresh_enrichment_result(
    value: PageProjectionEvidenceEnrichmentResult,
) -> PageProjectionEvidenceEnrichmentResult:
    if type(value) is not PageProjectionEvidenceEnrichmentResult:
        raise TypeError(
            "enrichment_result must be PageProjectionEvidenceEnrichmentResult"
        )
    try:
        fresh_request = PageProjectionEvidenceEnrichmentRequest(
            projection=value.request.projection
        )
        fresh = PageProjectionEvidenceEnrichmentActionizer().action(
            request=fresh_request
        )
    except (TypeError, ValueError) as error:
        raise AuthorityBoundEvidenceAdmissionError(
            "enrichment result is stale or malformed"
        ) from error
    if fresh != value:
        raise AuthorityBoundEvidenceAdmissionError(
            "enrichment result differs from deterministic derivation"
        )
    return fresh


def _fresh_reference_link(
    value: IngestionArtifactAuthorityLink,
) -> IngestionArtifactAuthorityLink:
    if type(value) is not IngestionArtifactAuthorityLink:
        raise TypeError("authority link must be IngestionArtifactAuthorityLink")
    fresh = IngestionArtifactAuthorityLink(
        asset_observation_id=value.asset_observation_id,
        source_id=value.source_id,
        document_id=value.document_id,
        artifact_verification_result_id=(value.artifact_verification_result_id),
    )
    if fresh != value:
        raise AuthorityBoundEvidenceAdmissionError(
            "reference authority link identity is stale"
        )
    return fresh


def _fresh_reference_binding(
    value: SearchReferenceAuthorityBinding,
) -> SearchReferenceAuthorityBinding:
    if type(value) is not SearchReferenceAuthorityBinding:
        raise TypeError(
            "authority binding must be SearchReferenceAuthorityBinding"
        )
    if type(value.ingestion_artifact_links) is not tuple:
        raise TypeError("authority links must be an immutable tuple")
    links = tuple(
        _fresh_reference_link(link) for link in value.ingestion_artifact_links
    )
    fresh = SearchReferenceAuthorityBinding(
        candidate_id=value.candidate_id,
        bibliographic_work_id=value.bibliographic_work_id,
        reference_identity_status=value.reference_identity_status,
        accepted_citekey=value.accepted_citekey,
        source_asset_id=value.source_asset_id,
        authority_binding_id=value.authority_binding_id,
        identity_decision_id=value.identity_decision_id,
        canonical_asset_decision_id=value.canonical_asset_decision_id,
        ingestion_artifact_links=links,
        authority_evidence_ids=value.authority_evidence_ids,
        state_projection_id=value.state_projection_id,
    )
    if fresh != value:
        raise AuthorityBoundEvidenceAdmissionError(
            "reference authority binding identity is stale"
        )
    return fresh


def _fresh_reference_authority(
    value: SearchReferenceAuthorityProjection,
) -> SearchReferenceAuthorityProjection:
    if type(value) is not SearchReferenceAuthorityProjection:
        raise TypeError(
            "reference_authority must be SearchReferenceAuthorityProjection"
        )
    try:
        if type(value.bindings) is not tuple:
            raise TypeError("authority bindings must be an immutable tuple")
        bindings = tuple(
            _fresh_reference_binding(binding) for binding in value.bindings
        )
        fresh = SearchReferenceAuthorityProjection(
            review_projection_id=value.review_projection_id,
            bindings=bindings,
        )
    except (AttributeError, TypeError, ValueError) as error:
        raise AuthorityBoundEvidenceAdmissionError(
            "reference authority is stale or malformed"
        ) from error
    if fresh != value:
        raise AuthorityBoundEvidenceAdmissionError(
            "reference authority identity is stale"
        )
    return fresh


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthorityBoundEvidenceAdmissionRequest(DataObjectActionRequest):
    """Bind exact A, B, and replay-current C inputs for one admission pass."""

    CONTRACT_NAME: ClassVar[str] = "authority-bound-evidence-admission-request"
    CONTRACT_VERSION: ClassVar[str] = "1.0"

    chunking_result: PageProjectionChunkingResult
    enrichment_result: PageProjectionEvidenceEnrichmentResult
    reference_authority: SearchReferenceAuthorityProjection
    expected_reference_authority_result_id: str
    request_id: str = field(init=False)

    def __post_init__(self) -> None:
        chunking = _fresh_chunking_result(self.chunking_result)
        enrichment = _fresh_enrichment_result(self.enrichment_result)
        authority = _fresh_reference_authority(self.reference_authority)
        expected = _require_identity(
            self.expected_reference_authority_result_id,
            label="expected References authority result ID",
        )
        if authority.result_id != expected:
            raise AuthorityBoundEvidenceAdmissionError(
                "References authority checkpoint is stale"
            )
        projection_id = chunking.request.projection_result.result_id
        if enrichment.page_projection_result_id != projection_id:
            raise AuthorityBoundEvidenceAdmissionError(
                "chunking and enrichment projection results differ"
            )
        if len(chunking.chunks) > _MAXIMUM_INPUT_CHUNKS:
            raise AuthorityBoundEvidenceAdmissionError(
                "admission input exceeds its fixed chunk bound"
            )
        object.__setattr__(
            self,
            "request_id",
            _identity(
                namespace=self.CONTRACT_NAME,
                material={
                    "chunking_result_id": chunking.result_id,
                    "contract_version": self.CONTRACT_VERSION,
                    "enrichment_result_id": enrichment.result_id,
                    "reference_authority_projection_id": (
                        authority.projection_id
                    ),
                    "reference_authority_result_id": authority.result_id,
                },
            ),
        )


def _fresh_admission_request(
    value: AuthorityBoundEvidenceAdmissionRequest,
) -> AuthorityBoundEvidenceAdmissionRequest:
    if type(value) is not AuthorityBoundEvidenceAdmissionRequest:
        raise TypeError(
            "request must be AuthorityBoundEvidenceAdmissionRequest"
        )
    fresh = AuthorityBoundEvidenceAdmissionRequest(
        chunking_result=value.chunking_result,
        enrichment_result=value.enrichment_result,
        reference_authority=value.reference_authority,
        expected_reference_authority_result_id=(
            value.expected_reference_authority_result_id
        ),
    )
    if fresh != value:
        raise AuthorityBoundEvidenceAdmissionError(
            "admission request identity is stale"
        )
    return fresh


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthorityBoundEvidenceAdmission(DataObjectModel):
    """Bind one admitted item to its exact A, B, and C evidence."""

    item: EvidenceItem
    chunk: PageProjectionChunk
    enrichment: PageProjectionEvidenceEnrichment
    reference_binding: SearchReferenceAuthorityBinding
    reference_link: IngestionArtifactAuthorityLink
    admission_id: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.item) is not EvidenceItem:
            raise TypeError("item must be EvidenceItem")
        if type(self.chunk) is not PageProjectionChunk:
            raise TypeError("chunk must be PageProjectionChunk")
        if type(self.enrichment) is not PageProjectionEvidenceEnrichment:
            raise TypeError(
                "enrichment must be PageProjectionEvidenceEnrichment"
            )
        if type(self.reference_binding) is not SearchReferenceAuthorityBinding:
            raise TypeError(
                "reference_binding must be SearchReferenceAuthorityBinding"
            )
        if type(self.reference_link) is not IngestionArtifactAuthorityLink:
            raise TypeError(
                "reference_link must be IngestionArtifactAuthorityLink"
            )
        expected = _evidence_item(
            chunk=self.chunk,
            enrichment=self.enrichment,
            binding=self.reference_binding,
            link=self.reference_link,
        )
        if self.item != expected:
            raise AuthorityBoundEvidenceAdmissionError(
                "admitted item differs from exact A+B+C derivation"
            )
        object.__setattr__(
            self,
            "admission_id",
            _identity(
                namespace="authority-bound-evidence-admission",
                material={
                    "chunk_id": self.chunk.chunk_id,
                    "enrichment_id": self.enrichment.enrichment_id,
                    "evidence_item_id": self.item.evidence_item_id,
                    "reference_binding_id": self.reference_binding.binding_id,
                    "reference_link_id": self.reference_link.link_id,
                },
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthorityBoundEvidenceOmission(DataObjectModel):
    """Retain one explicit fail-closed disposition for an unadmitted chunk."""

    chunk_id: str
    source_evidence_id: str
    reason: AuthorityBoundEvidenceOmissionReason
    related_ids: tuple[str, ...]
    omission_id: str = field(init=False)

    def __post_init__(self) -> None:
        _require_identity(self.chunk_id, label="omitted chunk ID")
        _require_identity(
            self.source_evidence_id,
            label="omitted source evidence ID",
        )
        if not isinstance(self.reason, AuthorityBoundEvidenceOmissionReason):
            raise TypeError(
                "reason must be AuthorityBoundEvidenceOmissionReason"
            )
        if type(self.related_ids) is not tuple:
            raise TypeError("related_ids must be an immutable tuple")
        for value in self.related_ids:
            _require_identity(value, label="related omission ID")
        if self.related_ids != tuple(sorted(set(self.related_ids))):
            raise AuthorityBoundEvidenceAdmissionError(
                "related omission IDs must use unique lexical order"
            )
        object.__setattr__(
            self,
            "omission_id",
            _identity(
                namespace="authority-bound-evidence-omission",
                material={
                    "chunk_id": self.chunk_id,
                    "reason": self.reason.value,
                    "related_ids": self.related_ids,
                    "source_evidence_id": self.source_evidence_id,
                },
            ),
        )


def _binding_matches_chunk(
    *,
    chunk: PageProjectionChunk,
    enrichment: PageProjectionEvidenceEnrichment,
) -> bool:
    binding = enrichment.binding
    return all(
        (
            binding.source_evidence_id == chunk.source_evidence_id,
            binding.page_projection_result_id
            == chunk.page_projection_result_id,
            binding.source_result_id == chunk.source_result_id,
            binding.reading_projection_result_id
            == chunk.reading_projection_result_id,
            binding.artifact_verification_result_id
            == chunk.artifact_verification_result_id,
            binding.source_id == chunk.source_id,
            binding.document_id == chunk.document_id,
            binding.source_page_id == chunk.source_page_id,
            binding.page_location_id == chunk.page_location_id,
            binding.page_projection_page_id == chunk.page_projection_page_id,
            binding.page_projection_block_id == chunk.page_projection_block_id,
            binding.style.value == chunk.style.value,
        )
    )


def _link_matches_chunk(
    *, chunk: PageProjectionChunk, link: IngestionArtifactAuthorityLink
) -> bool:
    return (
        link.source_id == chunk.source_id
        and link.document_id == chunk.document_id
        and link.artifact_verification_result_id
        == chunk.artifact_verification_result_id
    )


def _evidence_item_exceeds_limit(
    *,
    chunk: PageProjectionChunk,
    enrichment: PageProjectionEvidenceEnrichment,
    binding: SearchReferenceAuthorityBinding,
) -> bool:
    identity_values = (
        binding.bibliographic_work_id,
        binding.source_asset_id,
        chunk.reading_projection_result_id,
        chunk.source_page_id,
        chunk.source_evidence_id,
        *tuple(enrichment.source_span_ids),
    )
    return any(
        len(value) > EvidenceItem.MAX_ID_CHARACTERS for value in identity_values
    ) or any(
        (
            len(binding.accepted_citekey) > EvidenceItem.MAX_CITEKEY_CHARACTERS,
            chunk.printed_page_label is not None
            and len(chunk.printed_page_label)
            > EvidenceItem.MAX_PRINTED_PAGE_LABEL_CHARACTERS,
            len(enrichment.source_span_ids) > EvidenceItem.MAX_SOURCE_SPANS,
            len(chunk.text) > EvidenceItem.MAX_INDEXED_TEXT_CHARACTERS,
            len(enrichment.retained_text)
            > EvidenceItem.MAX_RETAINED_TEXT_CHARACTERS,
        )
    )


def _evidence_item(
    *,
    chunk: PageProjectionChunk,
    enrichment: PageProjectionEvidenceEnrichment,
    binding: SearchReferenceAuthorityBinding,
    link: IngestionArtifactAuthorityLink,
) -> EvidenceItem:
    if binding.reference_identity_status != "accepted":
        raise AuthorityBoundEvidenceAdmissionError(
            "References binding is not accepted authority"
        )
    if link not in binding.ingestion_artifact_links:
        raise AuthorityBoundEvidenceAdmissionError(
            "References link is absent from its authority binding"
        )
    if not _binding_matches_chunk(chunk=chunk, enrichment=enrichment):
        raise AuthorityBoundEvidenceAdmissionError(
            "Ingestion enrichment differs from its Search chunk"
        )
    if not _link_matches_chunk(chunk=chunk, link=link):
        raise AuthorityBoundEvidenceAdmissionError(
            "References authority differs from Ingestion lineage"
        )
    return EvidenceItem(
        corpus_role=AuthoringCorpusRole.REFERENCE_EVIDENCE,
        bibliographic_work_id=binding.bibliographic_work_id,
        reference_identity_status=ReferenceIdentityStatus.ACCEPTED,
        accepted_citekey=binding.accepted_citekey,
        source_asset_id=binding.source_asset_id,
        # The current prototype field predates the canonical Reading projection
        # name. Production admission binds the exact projection result identity.
        transcript_id=chunk.reading_projection_result_id,
        page_id=chunk.source_page_id,
        page_index=chunk.physical_page_index,
        printed_page_label=chunk.printed_page_label,
        block_id=chunk.source_evidence_id,
        source_span_ids=tuple(enrichment.source_span_ids),
        indexed_text=chunk.text,
        indexed_text_sha256=chunk.text_sha256,
        retained_text=enrichment.retained_text,
        retained_text_sha256=enrichment.retained_text_sha256,
        # Opaque producer warnings stay exact on ``enrichment``; translation
        # into Search-owned warning semantics would invent unavailable detail.
        warnings=(),
    )


def _omission(
    *,
    chunk: PageProjectionChunk,
    reason: AuthorityBoundEvidenceOmissionReason,
    related_ids: tuple[str, ...] = (),
) -> AuthorityBoundEvidenceOmission:
    return AuthorityBoundEvidenceOmission(
        chunk_id=chunk.chunk_id,
        source_evidence_id=chunk.source_evidence_id,
        reason=reason,
        related_ids=tuple(sorted(set(related_ids))),
    )


def _derive(
    request: AuthorityBoundEvidenceAdmissionRequest,
) -> tuple[
    tuple[AuthorityBoundEvidenceAdmission, ...],
    tuple[AuthorityBoundEvidenceOmission, ...],
    EvidenceCorpus,
]:
    entries: dict[str, PageProjectionEvidenceEntry] = {
        value.source_evidence_id: value
        for value in request.enrichment_result.entries
    }
    authority_matches: dict[
        tuple[str, str, str],
        list[
            tuple[
                SearchReferenceAuthorityBinding,
                IngestionArtifactAuthorityLink,
            ]
        ],
    ] = {}
    for binding in request.reference_authority.bindings:
        for link in binding.ingestion_artifact_links:
            key = (
                link.source_id,
                link.document_id,
                link.artifact_verification_result_id,
            )
            authority_matches.setdefault(key, []).append((binding, link))

    admissions: list[AuthorityBoundEvidenceAdmission] = []
    omissions: list[AuthorityBoundEvidenceOmission] = []
    for chunk in request.chunking_result.chunks:
        entry = entries.get(chunk.source_evidence_id)
        if entry is None:
            omissions.append(
                _omission(
                    chunk=chunk,
                    reason=(
                        AuthorityBoundEvidenceOmissionReason.MISSING_INGESTION_ENRICHMENT
                    ),
                )
            )
            continue
        if type(entry) is PageProjectionEvidenceUnavailable:
            omissions.append(
                _omission(
                    chunk=chunk,
                    reason=(
                        AuthorityBoundEvidenceOmissionReason.ENRICHMENT_UNAVAILABLE
                    ),
                    related_ids=(entry.disposition_id,),
                )
            )
            continue
        if type(entry) is not PageProjectionEvidenceEnrichment:
            raise AuthorityBoundEvidenceAdmissionError(
                "enrichment inventory contains an unsupported entry"
            )
        if not _binding_matches_chunk(chunk=chunk, enrichment=entry):
            omissions.append(
                _omission(
                    chunk=chunk,
                    reason=(
                        AuthorityBoundEvidenceOmissionReason.INCONSISTENT_BINDING
                    ),
                    related_ids=(entry.enrichment_id,),
                )
            )
            continue
        key = (
            chunk.source_id,
            chunk.document_id,
            chunk.artifact_verification_result_id,
        )
        matches = authority_matches.get(key, [])
        if not matches:
            omissions.append(
                _omission(
                    chunk=chunk,
                    reason=(
                        AuthorityBoundEvidenceOmissionReason.MISSING_REFERENCE_AUTHORITY
                    ),
                    related_ids=(entry.enrichment_id,),
                )
            )
            continue
        if len(matches) != 1:
            omissions.append(
                _omission(
                    chunk=chunk,
                    reason=(
                        AuthorityBoundEvidenceOmissionReason.INCONSISTENT_BINDING
                    ),
                    related_ids=(
                        entry.enrichment_id,
                        *(value[0].binding_id for value in matches),
                        *(value[1].link_id for value in matches),
                    ),
                )
            )
            continue
        binding, link = matches[0]
        if _evidence_item_exceeds_limit(
            chunk=chunk,
            enrichment=entry,
            binding=binding,
        ):
            omissions.append(
                _omission(
                    chunk=chunk,
                    reason=AuthorityBoundEvidenceOmissionReason.OVER_LIMIT,
                    related_ids=(
                        entry.enrichment_id,
                        binding.binding_id,
                        link.link_id,
                    ),
                )
            )
            continue
        try:
            item = _evidence_item(
                chunk=chunk,
                enrichment=entry,
                binding=binding,
                link=link,
            )
        except AuthorityBoundEvidenceAdmissionError:
            omissions.append(
                _omission(
                    chunk=chunk,
                    reason=(
                        AuthorityBoundEvidenceOmissionReason.INCONSISTENT_BINDING
                    ),
                    related_ids=(
                        entry.enrichment_id,
                        binding.binding_id,
                        link.link_id,
                    ),
                )
            )
            continue
        except (TypeError, ValueError) as error:
            raise AuthorityBoundEvidenceAdmissionError(
                "exact A+B+C values cannot construct EvidenceItem"
            ) from error
        admissions.append(
            AuthorityBoundEvidenceAdmission(
                item=item,
                chunk=chunk,
                enrichment=entry,
                reference_binding=binding,
                reference_link=link,
            )
        )
    corpus = EvidenceCorpus(
        admitted_role=AuthoringCorpusRole.REFERENCE_EVIDENCE,
        items=tuple(value.item for value in admissions),
    )
    return tuple(admissions), tuple(omissions), corpus


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthorityBoundEvidenceAdmissionResult(DataObjectActionResult):
    """Expose the only production manuscript-authoring corpus boundary."""

    CONTRACT_NAME: ClassVar[str] = "authority-bound-evidence-admission-result"
    CONTRACT_VERSION: ClassVar[str] = "1.0"
    COMPOSER_ID: ClassVar[str] = (
        "projectkoios.search.authority-bound-evidence-admission-composer"
    )
    COMPOSER_VERSION: ClassVar[str] = "1.0"

    request: AuthorityBoundEvidenceAdmissionRequest
    admissions: tuple[AuthorityBoundEvidenceAdmission, ...]
    omissions: tuple[AuthorityBoundEvidenceOmission, ...]
    corpus: EvidenceCorpus
    composer_id: str
    composer_version: str
    result_id: str = field(init=False)

    def __post_init__(self) -> None:
        fresh_request = _fresh_admission_request(self.request)
        if type(self.admissions) is not tuple or any(
            type(value) is not AuthorityBoundEvidenceAdmission
            for value in self.admissions
        ):
            raise TypeError("admissions must contain exact admission values")
        if type(self.omissions) is not tuple or any(
            type(value) is not AuthorityBoundEvidenceOmission
            for value in self.omissions
        ):
            raise TypeError("omissions must contain exact omission values")
        if type(self.corpus) is not EvidenceCorpus:
            raise TypeError("corpus must be EvidenceCorpus")
        expected_admissions, expected_omissions, expected_corpus = _derive(
            fresh_request
        )
        if (
            self.admissions != expected_admissions
            or self.omissions != expected_omissions
            or self.corpus != expected_corpus
        ):
            raise AuthorityBoundEvidenceAdmissionError(
                "admission output differs from deterministic A+B+C join"
            )
        if self.composer_id != self.COMPOSER_ID or (
            self.composer_version != self.COMPOSER_VERSION
        ):
            raise AuthorityBoundEvidenceAdmissionError(
                "admission composer identity is unsupported"
            )
        if len(self.admissions) + len(self.omissions) != len(
            self.request.chunking_result.chunks
        ):
            raise AuthorityBoundEvidenceAdmissionError(
                "admission result does not cover every exact chunk"
            )
        object.__setattr__(
            self,
            "result_id",
            _identity(
                namespace=self.CONTRACT_NAME,
                material={
                    "admission_ids": tuple(
                        value.admission_id for value in self.admissions
                    ),
                    "composer_id": self.composer_id,
                    "composer_version": self.composer_version,
                    "contract_version": self.CONTRACT_VERSION,
                    "corpus_id": self.corpus.corpus_id,
                    "omission_ids": tuple(
                        value.omission_id for value in self.omissions
                    ),
                    "reference_authority_result_id": (
                        self.request.reference_authority.result_id
                    ),
                    "request_id": self.request.request_id,
                },
            ),
        )


class AuthorityBoundEvidenceAdmissionComposer(
    DataObjectActionizer[
        AuthorityBoundEvidenceAdmissionRequest,
        AuthorityBoundEvidenceAdmissionResult,
    ]
):
    """Derive the accepted-only production corpus and explicit omissions."""

    __slots__ = ()

    def action(
        self, *, request: AuthorityBoundEvidenceAdmissionRequest
    ) -> AuthorityBoundEvidenceAdmissionResult:
        """Return the complete deterministic authority admission result."""
        request = _fresh_admission_request(request)
        admissions, omissions, corpus = _derive(request)
        return AuthorityBoundEvidenceAdmissionResult(
            request=request,
            admissions=admissions,
            omissions=omissions,
            corpus=corpus,
            composer_id=AuthorityBoundEvidenceAdmissionResult.COMPOSER_ID,
            composer_version=(
                AuthorityBoundEvidenceAdmissionResult.COMPOSER_VERSION
            ),
        )


def _fresh_admission_result(
    value: AuthorityBoundEvidenceAdmissionResult,
) -> AuthorityBoundEvidenceAdmissionResult:
    if type(value) is not AuthorityBoundEvidenceAdmissionResult:
        raise TypeError(
            "admission must be AuthorityBoundEvidenceAdmissionResult"
        )
    fresh = AuthorityBoundEvidenceAdmissionComposer().action(
        request=value.request
    )
    if fresh != value:
        raise AuthorityBoundEvidenceAdmissionError(
            "authority admission result is stale"
        )
    return fresh


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthorityBoundEvidenceRetrievalResult(DataObjectActionResult):
    """Bind one lexical result to exact accepted-authority admission."""

    CONTRACT_NAME: ClassVar[str] = "authority-bound-evidence-retrieval-result"
    CONTRACT_VERSION: ClassVar[str] = "1.0"
    RETRIEVER_ID: ClassVar[str] = (
        "projectkoios.search.authority-bound-deterministic-lexical-retriever"
    )

    admission: AuthorityBoundEvidenceAdmissionResult
    retrieval: EvidenceRetrievalResult
    retriever_id: str
    result_id: str = field(init=False)

    def __post_init__(self) -> None:
        admission = _fresh_admission_result(self.admission)
        if type(self.retrieval) is not EvidenceRetrievalResult:
            raise TypeError("retrieval must be EvidenceRetrievalResult")
        _require_identity(self.retriever_id, label="authority retriever ID")
        if self.retriever_id != self.RETRIEVER_ID:
            raise AuthorityBoundEvidenceAdmissionError(
                "authority retriever identity is unsupported"
            )
        if self.retrieval.corpus_id != admission.corpus.corpus_id:
            raise AuthorityBoundEvidenceAdmissionError(
                "retrieval corpus differs from authority admission"
            )
        expected = DeterministicLexicalEvidenceRetriever(
            corpus=admission.corpus
        ).action(request=self.retrieval.request)
        if self.retrieval != expected:
            raise AuthorityBoundEvidenceAdmissionError(
                "retrieval differs from deterministic admitted corpus"
            )
        object.__setattr__(
            self,
            "result_id",
            _identity(
                namespace=self.CONTRACT_NAME,
                material={
                    "admission_result_id": admission.result_id,
                    "contract_version": self.CONTRACT_VERSION,
                    "reference_authority_result_id": (
                        admission.request.reference_authority.result_id
                    ),
                    "retrieval_result_id": self.retrieval.result_id,
                    "retriever_id": self.retriever_id,
                },
            ),
        )


class AuthorityBoundDeterministicLexicalEvidenceRetriever(
    DataObjectActionizer[
        EvidenceRetrievalRequest,
        AuthorityBoundEvidenceRetrievalResult,
    ]
):
    """Retrieve only from an exact accepted-authority admission result."""

    __slots__ = ("_admission", "_delegate")

    IMPLEMENTATION_ID: ClassVar[str] = (
        AuthorityBoundEvidenceRetrievalResult.RETRIEVER_ID
    )

    def __init__(
        self, *, admission: AuthorityBoundEvidenceAdmissionResult
    ) -> None:
        self._admission = _fresh_admission_result(admission)
        self._delegate = DeterministicLexicalEvidenceRetriever(
            corpus=self._admission.corpus
        )

    @property
    def admission(self) -> AuthorityBoundEvidenceAdmissionResult:
        """Return the exact production admission bound to this retriever."""
        return self._admission

    def action(
        self, *, request: EvidenceRetrievalRequest
    ) -> AuthorityBoundEvidenceRetrievalResult:
        """Return retrieval bound to accepted authority and its checkpoint."""
        if type(request) is not EvidenceRetrievalRequest:
            raise TypeError("request must be EvidenceRetrievalRequest")
        return AuthorityBoundEvidenceRetrievalResult(
            admission=self._admission,
            retrieval=self._delegate.action(request=request),
            retriever_id=self.IMPLEMENTATION_ID,
        )

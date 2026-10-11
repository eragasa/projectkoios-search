"""Authority-bound production manuscript evidence tests."""

from __future__ import annotations

import ast
import hashlib
from dataclasses import replace
from pathlib import Path

import pytest
from projectkoios.ingestion.page.projection.enrichment.actionizer import (
    PageProjectionEvidenceEnrichmentActionizer,
)
from projectkoios.ingestion.page.projection.enrichment.request import (
    PageProjectionEvidenceEnrichmentRequest,
)
from projectkoios.references.course_reference_authority import (
    IngestionArtifactAuthorityLink,
    SearchReferenceAuthorityBinding,
    SearchReferenceAuthorityProjection,
)
from projectkoios.search.authority_bound_evidence import (
    AuthorityBoundDeterministicLexicalEvidenceRetriever,
    AuthorityBoundEvidenceAdmissionComposer,
    AuthorityBoundEvidenceAdmissionError,
    AuthorityBoundEvidenceAdmissionRequest,
    AuthorityBoundEvidenceAdmissionResult,
    AuthorityBoundEvidenceOmissionReason,
)
from projectkoios.search.evidence_retrieval import (
    AuthoringPurpose,
    EvidenceRetrievalOutcome,
    EvidenceRetrievalRequest,
    ReferenceIdentityStatus,
)

from tests.projectkoios.search.page_projection_chunking.fixture import (
    chunking as chunking_fixture,
)

derive_chunking_result = chunking_fixture.derive_chunking_result


def _content_id(namespace: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"{namespace}:sha256:{digest}"


def _authority(
    *,
    source_id: str = "source:book",
    document_id: str | None = None,
    artifact_verification_result_id: str | None = None,
) -> SearchReferenceAuthorityProjection:
    chunk = tuple(derive_chunking_result().chunks)[0]
    asset_observation_id = _content_id("catalog-asset-observation", "asset")
    link = IngestionArtifactAuthorityLink(
        asset_observation_id=asset_observation_id,
        source_id=source_id,
        document_id=document_id or chunk.document_id,
        artifact_verification_result_id=(
            artifact_verification_result_id
            or chunk.artifact_verification_result_id
        ),
    )
    evidence_ids = tuple(
        sorted(
            (
                _content_id("human-review-decision", "identity"),
                _content_id("human-review-decision", "asset"),
                _content_id("runtime-asset-evidence", "available"),
                link.link_id,
            )
        )
    )
    binding = SearchReferenceAuthorityBinding(
        candidate_id=_content_id("reference-candidate", "candidate"),
        bibliographic_work_id=_content_id("bibliographic-work", "work"),
        reference_identity_status="accepted",
        accepted_citekey="canonicalBook",
        source_asset_id=_content_id("source-asset", "asset"),
        authority_binding_id=_content_id(
            "reference-source-asset-binding", "binding"
        ),
        identity_decision_id=_content_id("human-review-decision", "identity"),
        canonical_asset_decision_id=_content_id(
            "human-review-decision", "asset"
        ),
        ingestion_artifact_links=(link,),
        authority_evidence_ids=evidence_ids,
        state_projection_id=_content_id("reference-state-projection", "state"),
    )
    return SearchReferenceAuthorityProjection(
        review_projection_id=_content_id("review-projection", "review"),
        bindings=(binding,),
    )


def _request(
    *,
    authority: SearchReferenceAuthorityProjection | None = None,
    expected_result_id: str | None = None,
) -> AuthorityBoundEvidenceAdmissionRequest:
    chunks = derive_chunking_result()
    projection = chunks.request.projection_result
    enrichment = PageProjectionEvidenceEnrichmentActionizer().action(
        request=PageProjectionEvidenceEnrichmentRequest(projection=projection)
    )
    selected = authority or _authority()
    return AuthorityBoundEvidenceAdmissionRequest(
        chunking_result=chunks,
        enrichment_result=enrichment,
        reference_authority=selected,
        expected_reference_authority_result_id=(
            expected_result_id or selected.result_id
        ),
    )


def _admission() -> AuthorityBoundEvidenceAdmissionResult:
    return AuthorityBoundEvidenceAdmissionComposer().action(request=_request())


def _retrieval_request() -> EvidenceRetrievalRequest:
    return EvidenceRetrievalRequest(
        purpose=AuthoringPurpose.MANUSCRIPT_AUTHORING,
        query="canonical paragraph",
        target_id="claim:solid-state",
        bibliographic_work_ids=(),
        required_bibliographic_work_ids=(),
        result_limit=4,
        per_work_limit=2,
        max_total_text_characters=20_000,
    )


def test__admission__joins_exact_A_B_C_and_omits_unavailable_caption() -> None:
    first = _admission()
    second = AuthorityBoundEvidenceAdmissionComposer().action(
        request=first.request
    )

    assert second == first
    assert len(first.admissions) == 1
    assert len(first.omissions) == 1
    assert first.omissions[0].reason is (
        AuthorityBoundEvidenceOmissionReason.ENRICHMENT_UNAVAILABLE
    )
    admitted = first.admissions[0]
    assert admitted.item.reference_identity_status is (
        ReferenceIdentityStatus.ACCEPTED
    )
    assert admitted.item.accepted_citekey == "canonicalBook"
    assert admitted.item.source_asset_id == (
        admitted.reference_binding.source_asset_id
    )
    assert admitted.item.indexed_text == "Canonical paragraph."
    assert admitted.item.retained_text == admitted.enrichment.retained_text
    assert admitted.item.source_span_ids == tuple(
        admitted.enrichment.source_span_ids
    )
    assert admitted.reference_link.source_id == "source:book"
    assert admitted.reference_link.document_id == (
        "reading-evidence-document:sha256:"
        "8a7358d8dafbf7da3d58f6b3233c9db0284f4ee0ec7d4891da1106bfd7942871"
    )
    assert admitted.reference_link.artifact_verification_result_id == (
        "managed-artifact-verification-result:sha256:"
        "5c68aeb1065e4215cbfb07e12dcb0b54329a1010a58c04bb54d39d3469b60be0"
    )
    assert first.corpus.items == (admitted.item,)
    assert first.result_id.startswith(
        "authority-bound-evidence-admission-result:sha256:"
    )


def test__admission__requires_exact_current_reference_checkpoint() -> None:
    authority = _authority()
    with pytest.raises(
        AuthorityBoundEvidenceAdmissionError,
        match="checkpoint is stale",
    ):
        _request(
            authority=authority,
            expected_result_id=_content_id(
                "search-reference-authority-result", "stale"
            ),
        )


def test__admission__rejects_force_mutated_reference_result_identity() -> None:
    authority = _authority()
    changed = _content_id("search-reference-authority-result", "changed")
    object.__setattr__(authority, "result_id", changed)

    with pytest.raises(
        AuthorityBoundEvidenceAdmissionError,
        match="reference authority identity is stale",
    ):
        _request(authority=authority, expected_result_id=changed)


@pytest.mark.parametrize(
    "authority",
    (
        _authority(source_id="source:other-book"),
        _authority(document_id=_content_id("reading-evidence-document", "x")),
        _authority(
            artifact_verification_result_id=_content_id(
                "managed-artifact-verification-result", "x"
            )
        ),
    ),
)
def test__admission__does_not_admit_independent_lineage_mismatch(
    authority: SearchReferenceAuthorityProjection,
) -> None:
    result = AuthorityBoundEvidenceAdmissionComposer().action(
        request=_request(authority=authority)
    )

    assert result.admissions == ()
    assert result.corpus.items == ()
    assert tuple(value.reason for value in result.omissions) == (
        AuthorityBoundEvidenceOmissionReason.MISSING_REFERENCE_AUTHORITY,
        AuthorityBoundEvidenceOmissionReason.ENRICHMENT_UNAVAILABLE,
    )


def test__admission__does_not_admit_absent_or_ambiguous_authority() -> None:
    empty = SearchReferenceAuthorityProjection(
        review_projection_id=_content_id("review-projection", "empty"),
        bindings=(),
    )
    original = _authority().bindings[0]
    duplicate = replace(
        original,
        bibliographic_work_id=_content_id("bibliographic-work", "second"),
        accepted_citekey="secondBook",
        authority_binding_id=_content_id(
            "reference-source-asset-binding", "second"
        ),
    )
    ambiguous = SearchReferenceAuthorityProjection(
        review_projection_id=_content_id("review-projection", "ambiguous"),
        bindings=tuple(
            sorted((original, duplicate), key=lambda value: value.binding_id)
        ),
    )

    missing = AuthorityBoundEvidenceAdmissionComposer().action(
        request=_request(authority=empty)
    )
    conflicting = AuthorityBoundEvidenceAdmissionComposer().action(
        request=_request(authority=ambiguous)
    )
    assert missing.omissions[0].reason is (
        AuthorityBoundEvidenceOmissionReason.MISSING_REFERENCE_AUTHORITY
    )
    assert conflicting.omissions[0].reason is (
        AuthorityBoundEvidenceOmissionReason.INCONSISTENT_BINDING
    )
    assert missing.admissions == conflicting.admissions == ()


@pytest.mark.parametrize(
    "field_name",
    (
        "source_evidence_id",
        "source_id",
        "document_id",
        "artifact_verification_result_id",
        "source_page_id",
        "page_projection_page_id",
        "page_projection_block_id",
    ),
)
def test__admission__rejects_force_mutated_ingestion_binding(
    field_name: str,
) -> None:
    request = _request()
    enrichment = tuple(request.enrichment_result.entries)[0]
    assert hasattr(enrichment, "binding")
    object.__setattr__(
        enrichment.binding,
        field_name,
        _content_id("forced-mismatch", field_name),
    )

    with pytest.raises(
        AuthorityBoundEvidenceAdmissionError,
        match="enrichment result differs",
    ):
        AuthorityBoundEvidenceAdmissionComposer().action(request=request)


def test__admission__binds_reference_supersession_to_new_result() -> None:
    original = _authority()
    original_binding = original.bindings[0]
    replacement_binding = replace(
        original_binding,
        source_asset_id=_content_id("source-asset", "replacement"),
        canonical_asset_decision_id=_content_id(
            "human-review-decision", "replacement-asset"
        ),
    )
    replacement = SearchReferenceAuthorityProjection(
        review_projection_id=original.review_projection_id,
        bindings=(replacement_binding,),
    )
    first = AuthorityBoundEvidenceAdmissionComposer().action(
        request=_request(authority=original)
    )
    second = AuthorityBoundEvidenceAdmissionComposer().action(
        request=_request(authority=replacement)
    )

    assert second.result_id != first.result_id
    assert second.admissions[0].item.source_asset_id == (
        replacement_binding.source_asset_id
    )
    with pytest.raises(
        AuthorityBoundEvidenceAdmissionError,
        match="checkpoint is stale",
    ):
        _request(
            authority=replacement,
            expected_result_id=original.result_id,
        )


def test__admission_result__rejects_changed_complete_output() -> None:
    result = _admission()
    changed_item = replace(
        result.admissions[0].item,
        source_asset_id=_content_id("source-asset", "changed"),
    )

    with pytest.raises(
        AuthorityBoundEvidenceAdmissionError,
        match="differs from deterministic",
    ):
        replace(result, admissions=())
    with pytest.raises(
        AuthorityBoundEvidenceAdmissionError,
        match=r"exact A\+B\+C derivation",
    ):
        replace(result.admissions[0], item=changed_item)


def test__production_retriever__binds_admission_and_authority_result() -> None:
    admission = _admission()
    result = AuthorityBoundDeterministicLexicalEvidenceRetriever(
        admission=admission
    ).action(request=_retrieval_request())

    assert result.admission == admission
    assert result.retrieval.outcome is (
        EvidenceRetrievalOutcome.EVIDENCE_AVAILABLE
    )
    assert result.retrieval.evidence[0].item == admission.admissions[0].item
    assert result.result_id.startswith(
        "authority-bound-evidence-retrieval-result:sha256:"
    )
    with pytest.raises(
        AuthorityBoundEvidenceAdmissionError,
        match="retriever identity is unsupported",
    ):
        replace(
            result,
            retriever_id=_content_id("unsupported-retriever", "changed"),
        )


def test__production_retriever__rejects_raw_corpus() -> None:
    with pytest.raises(
        TypeError,
        match="AuthorityBoundEvidenceAdmissionResult",
    ):
        AuthorityBoundDeterministicLexicalEvidenceRetriever(
            admission=_admission().corpus,  # type: ignore[arg-type]
        )


def test__module__uses_only_public_ingestion_enrichment_leaf() -> None:
    source = (
        Path(__file__).resolve().parents[3]
        / "src/python/projectkoios/search/authority_bound_evidence.py"
    )
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imports = tuple(
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("projectkoios.ingestion")
    )

    assert imports
    assert all(
        value.startswith("projectkoios.ingestion.page.projection.enrichment")
        for value in imports
    )
    text = source.read_text(encoding="utf-8")
    assert "CleanTranscript" not in text
    assert "ReadingEvidenceDocument" not in text
    assert "ReadingEvidenceSourceResult" not in text

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
from projectkoios.references.courses.authority.evidence import (
    IngestionArtifactAuthorityLink,
)
from projectkoios.references.courses.authority.search_projection import (
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
    AuthorityBoundEvidenceRetrievalRequest,
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
    request = _request(authority=authority)
    changed = _content_id("search-reference-authority-result", "changed")
    object.__setattr__(authority, "result_id", changed)

    with pytest.raises(
        AuthorityBoundEvidenceAdmissionError,
        match="reference authority identity is stale",
    ):
        AuthorityBoundEvidenceAdmissionComposer().action(request=request)


def test__admission__rejects_force_mutated_expected_checkpoint() -> None:
    request = _request()
    object.__setattr__(
        request,
        "expected_reference_authority_result_id",
        _content_id("search-reference-authority-result", "forged"),
    )

    with pytest.raises(
        AuthorityBoundEvidenceAdmissionError,
        match="checkpoint is stale",
    ):
        AuthorityBoundEvidenceAdmissionComposer().action(request=request)


@pytest.mark.parametrize(
    ("field_name", "changed"),
    (
        ("candidate_id", _content_id("reference-candidate", "forged")),
        (
            "bibliographic_work_id",
            _content_id("bibliographic-work", "forged"),
        ),
        ("reference_identity_status", "candidate"),
        ("accepted_citekey", "forgedBook"),
        ("source_asset_id", _content_id("source-asset", "forged")),
        (
            "authority_binding_id",
            _content_id("reference-source-asset-binding", "forged"),
        ),
        (
            "identity_decision_id",
            _content_id("human-review-decision", "forged-identity"),
        ),
        (
            "canonical_asset_decision_id",
            _content_id("human-review-decision", "forged-asset"),
        ),
        (
            "authority_evidence_ids",
            (_content_id("runtime-asset-evidence", "forged"),),
        ),
        (
            "state_projection_id",
            _content_id("reference-state-projection", "forged"),
        ),
        (
            "binding_id",
            _content_id("search-reference-authority-binding", "forged"),
        ),
    ),
)
def test__admission__rejects_force_mutated_reference_binding(
    field_name: str,
    changed: object,
) -> None:
    authority = _authority()
    request = _request(authority=authority)
    checkpoint = authority.result_id
    object.__setattr__(authority.bindings[0], field_name, changed)
    assert authority.result_id == checkpoint

    with pytest.raises(
        AuthorityBoundEvidenceAdmissionError,
        match="reference authority",
    ):
        AuthorityBoundEvidenceAdmissionComposer().action(request=request)


@pytest.mark.parametrize(
    ("field_name", "changed"),
    (
        (
            "asset_observation_id",
            _content_id("catalog-asset-observation", "forged"),
        ),
        ("source_id", "source:forged-book"),
        (
            "document_id",
            _content_id("reading-evidence-document", "forged"),
        ),
        (
            "artifact_verification_result_id",
            _content_id("managed-artifact-verification-result", "forged"),
        ),
        (
            "link_id",
            _content_id("ingestion-artifact-authority-link", "forged"),
        ),
    ),
)
def test__admission__rejects_force_mutated_reference_link(
    field_name: str,
    changed: str,
) -> None:
    authority = _authority()
    request = _request(authority=authority)
    checkpoint = authority.result_id
    link = authority.bindings[0].ingestion_artifact_links[0]
    object.__setattr__(link, field_name, changed)
    assert authority.result_id == checkpoint

    with pytest.raises(
        AuthorityBoundEvidenceAdmissionError,
        match="reference authority",
    ):
        AuthorityBoundEvidenceAdmissionComposer().action(request=request)


@pytest.mark.parametrize(
    "mutation",
    ("replacement", "removal", "duplication", "wrong-container"),
)
def test__admission__rejects_force_mutated_link_inventory(
    mutation: str,
) -> None:
    authority = _authority()
    request = _request(authority=authority)
    binding = authority.bindings[0]
    link = binding.ingestion_artifact_links[0]
    replacement = IngestionArtifactAuthorityLink(
        asset_observation_id=link.asset_observation_id,
        source_id="source:replacement",
        document_id=link.document_id,
        artifact_verification_result_id=(link.artifact_verification_result_id),
    )
    changed: object
    if mutation == "replacement":
        changed = (replacement,)
    elif mutation == "removal":
        changed = ()
    elif mutation == "duplication":
        changed = (link, link)
    else:
        changed = [link]
    object.__setattr__(binding, "ingestion_artifact_links", changed)

    with pytest.raises(
        AuthorityBoundEvidenceAdmissionError,
        match="reference authority",
    ):
        AuthorityBoundEvidenceAdmissionComposer().action(request=request)


@pytest.mark.parametrize(
    "mutation",
    (
        "review-projection-id",
        "binding-replacement",
        "binding-removal",
        "binding-duplication",
        "binding-wrong-container",
        "projection-id",
    ),
)
def test__admission__rejects_force_mutated_outer_projection(
    mutation: str,
) -> None:
    authority = _authority()
    request = _request(authority=authority)
    original = authority.bindings[0]
    replacement = replace(
        original,
        bibliographic_work_id=_content_id(
            "bibliographic-work", "outer-replacement"
        ),
    )
    if mutation == "review-projection-id":
        field_name = "review_projection_id"
        changed: object = _content_id("review-projection", "forged")
    elif mutation == "binding-replacement":
        field_name = "bindings"
        changed = (replacement,)
    elif mutation == "binding-removal":
        field_name = "bindings"
        changed = ()
    elif mutation == "binding-duplication":
        field_name = "bindings"
        changed = (original, original)
    elif mutation == "binding-wrong-container":
        field_name = "bindings"
        changed = [original]
    else:
        field_name = "projection_id"
        changed = _content_id("search-reference-authority-projection", "forged")
    object.__setattr__(authority, field_name, changed)

    with pytest.raises(
        AuthorityBoundEvidenceAdmissionError,
        match="reference authority",
    ):
        AuthorityBoundEvidenceAdmissionComposer().action(request=request)


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
    request = AuthorityBoundEvidenceRetrievalRequest(
        admission=admission,
        retrieval_request=_retrieval_request(),
    )
    result = AuthorityBoundDeterministicLexicalEvidenceRetriever().action(
        request=request
    )

    assert result.request == request
    assert result.request.admission == admission
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
        AuthorityBoundEvidenceRetrievalRequest(
            admission=_admission().corpus,  # type: ignore[arg-type]
            retrieval_request=_retrieval_request(),
        )


def test__production_retriever__rejects_mutated_lexical_request() -> None:
    request = AuthorityBoundEvidenceRetrievalRequest(
        admission=_admission(),
        retrieval_request=_retrieval_request(),
    )
    object.__setattr__(request.retrieval_request, "query", "forged query")

    with pytest.raises(
        AuthorityBoundEvidenceAdmissionError,
        match="lexical retrieval request is stale",
    ):
        AuthorityBoundDeterministicLexicalEvidenceRetriever().action(
            request=request
        )


def test__production_retriever__rejects_mutated_admission_field() -> None:
    request = AuthorityBoundEvidenceRetrievalRequest(
        admission=_admission(),
        retrieval_request=_retrieval_request(),
    )
    object.__setattr__(request, "admission", request.admission.corpus)

    with pytest.raises(
        TypeError,
        match="AuthorityBoundEvidenceAdmissionResult",
    ):
        AuthorityBoundDeterministicLexicalEvidenceRetriever().action(
            request=request
        )


def _production_module_imports() -> tuple[tuple[str, ...], str]:
    source = (
        Path(__file__).resolve().parents[3]
        / "src/python/projectkoios/search/authority_bound_evidence.py"
    )
    text = source.read_text(encoding="utf-8")
    tree = ast.parse(text)
    imports = tuple(
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    )
    return imports, text


def test__module__uses_only_public_ingestion_enrichment_leaf() -> None:
    imports, text = _production_module_imports()
    ingestion_imports = tuple(
        value for value in imports if value.startswith("projectkoios.ingestion")
    )

    assert ingestion_imports
    assert all(
        value.startswith("projectkoios.ingestion.page.projection.enrichment")
        for value in ingestion_imports
    )
    assert "CleanTranscript" not in text
    assert "ReadingEvidenceDocument" not in text
    assert "ReadingEvidenceSourceResult" not in text


def test__module__uses_exact_references_courses_authority_leaf() -> None:
    imports, text = _production_module_imports()
    references_imports = tuple(
        value
        for value in imports
        if value.startswith("projectkoios.references")
    )

    assert references_imports == (
        "projectkoios.references.courses.authority.evidence",
        "projectkoios.references.courses.authority.search_projection",
    )
    assert "course_reference_authority" not in text

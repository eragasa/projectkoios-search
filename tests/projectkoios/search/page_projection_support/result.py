"""Build the exact typed result observed by the copied producer fixture."""

from __future__ import annotations

from projectkoios.ingestion.artifact.managed.verification.evidence import (
    ManagedArtifactVerificationEvidence,
    ManagedArtifactVerificationEvidenceInventory,
)
from projectkoios.ingestion.artifact.managed.verification.request import (
    ManagedArtifactVerificationRequest,
)
from projectkoios.ingestion.artifact.managed.verification.result import (
    ManagedArtifactVerificationResult,
)
from projectkoios.ingestion.page.projection.actionizer import (
    PageProjectionActionizer,
)
from projectkoios.ingestion.page.projection.request import PageProjectionRequest
from projectkoios.ingestion.page.projection.result import PageProjectionResult
from projectkoios.ingestion.transcript.reading.evidence.inventory.definition import (  # noqa: E501
    ReadingEvidenceInventory,
)
from projectkoios.ingestion.transcript.reading.evidence.source.request import (
    ReadingEvidenceSourceRequest,
)
from projectkoios.ingestion.transcript.reading.evidence.source.result import (
    ReadingEvidenceSourceResult,
)

from tests.projectkoios.search.page_projection_support.page_projection import (
    PageProjectionMixedVisualFixture,
    PageProjectionObservationFixture,
)

_PROVIDER_ID = "page-projection-test-provider:1.0"
_VERIFIER_ID = "page-projection-test-verifier:1.0"
_AUTHORITY_ID = "page-projection-test-authority"
_SOURCE_PROVIDER_ID = "page-projection-test-source-provider:1.0"
_SOURCE_VERIFICATION_ID = "page-projection-test-source-verification"


def build_page_projection_result() -> PageProjectionResult:
    """Return the real typed synthetic result behind the producer bytes."""

    fixture = PageProjectionMixedVisualFixture.build()
    document = fixture.document
    inventory = ReadingEvidenceInventory.observe(document)
    measures = inventory.measures
    source_request = ReadingEvidenceSourceRequest(
        provider_source_id="page-projection-test-source",
        document_id=document.document_id,
        projection_result_id=fixture.canonical.result_id,
        inventory_id=inventory.inventory_id,
        maximum_page_count=max(measures.page_count, 1),
        maximum_block_count=max(measures.block_count, 1),
        maximum_artifact_count=max(measures.artifact_count, 1),
        maximum_provider_record_count=max(measures.block_count, 1),
        authority_id=_AUTHORITY_ID,
    )
    source_result = ReadingEvidenceSourceResult(
        request=source_request,
        document=document,
        inventory=inventory,
        projection_result_id=fixture.canonical.result_id,
        provider_implementation_id=_SOURCE_PROVIDER_ID,
        provider_verification_id=_SOURCE_VERIFICATION_ID,
    )
    references = document.managed_artifacts
    verification_request = ManagedArtifactVerificationRequest(
        references=references,
        provider_implementation_id=_PROVIDER_ID,
        authority_id=_AUTHORITY_ID,
        maximum_artifact_bytes=max(
            reference.byte_length for reference in references
        ),
        maximum_aggregate_bytes=references.aggregate_byte_length,
        stream_chunk_bytes=1,
    )
    verification_evidence = ManagedArtifactVerificationEvidenceInventory(
        references,
        *(
            ManagedArtifactVerificationEvidence(
                reference=reference,
                observed_sha256=reference.sha256,
                observed_byte_length=reference.byte_length,
                observed_media_type=reference.media_type,
                provider_implementation_id=_PROVIDER_ID,
                verifier_implementation_id=_VERIFIER_ID,
            )
            for reference in references
        ),
    )
    verification_result = ManagedArtifactVerificationResult(
        request=verification_request,
        evidence=verification_evidence,
        verifier_implementation_id=_VERIFIER_ID,
    )
    request = PageProjectionRequest(
        source_result=source_result,
        artifact_verification_result=verification_result,
        include_figure_captions=True,
    )
    return PageProjectionActionizer().action(request=request)


def observe_page_projection_result(
    result: PageProjectionResult,
) -> dict[str, object]:
    """Return the producer-owned sanitized observation shape."""

    return PageProjectionObservationFixture(result=result).observation()

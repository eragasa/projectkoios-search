"""Deterministic foundation values for typed reading-evidence fixtures.

This module centralizes small synthetic identities, pages, spans, streams, and
visual evidence used to reconstruct the exact Ingestion page-projection result.
It performs no file access, extraction, model execution, or publication.

Notes
-----
Values intentionally use obvious synthetic text and identities so no protected
source content or private locator can enter the cross-repository fixture.
"""

from __future__ import annotations

from dataclasses import dataclass

from projectkoios.ingestion.artifact.managed.inventory import (
    ManagedArtifactReferenceInventory,
)
from projectkoios.ingestion.artifact.managed.media.type import (
    ManagedArtifactMediaType,
)
from projectkoios.ingestion.artifact.managed.reference import (
    ManagedArtifactReference,
)
from projectkoios.ingestion.sha256.hash import SHA256Hash
from projectkoios.ingestion.transcript.reading.evidence.association.evidence import (  # noqa: E501
    ReadingAssociationEvidence,
)
from projectkoios.ingestion.transcript.reading.evidence.association.inventory import (  # noqa: E501
    ReadingAssociationEvidenceInventory,
)
from projectkoios.ingestion.transcript.reading.evidence.association.role import (  # noqa: E501
    ReadingAssociationRole,
)
from projectkoios.ingestion.transcript.reading.evidence.identity.definition import (  # noqa: E501
    ReadingEvidenceIdentity,
)
from projectkoios.ingestion.transcript.reading.evidence.identity.inventory import (  # noqa: E501
    ReadingEvidenceIdentityInventory,
)
from projectkoios.ingestion.transcript.reading.evidence.identity.kind import (
    ReadingEvidenceIdentityKind,
)
from projectkoios.ingestion.transcript.reading.evidence.input.producer.lineage import (  # noqa: E501
    ReadingProducerLineage,
)
from projectkoios.ingestion.transcript.reading.evidence.input.visual.assessment import (  # noqa: E501
    ReadingVisualAssessment,
)
from projectkoios.ingestion.transcript.reading.evidence.label.inventory import (
    ReadingSourceLabelInventory,
)
from projectkoios.ingestion.transcript.reading.evidence.page.location import (
    ReadingPageLocation,
)
from projectkoios.ingestion.transcript.reading.evidence.span.evidence import (
    ReadingSourceSpanEvidence,
)
from projectkoios.ingestion.transcript.reading.evidence.span.geometry import (
    ReadingBoundingBox,
)
from projectkoios.ingestion.transcript.reading.evidence.span.inventory import (
    ReadingSourceSpanEvidenceInventory,
)
from projectkoios.ingestion.transcript.reading.evidence.status.review import (
    ReadingReviewStatus,
)
from projectkoios.ingestion.transcript.reading.evidence.status.visual import (
    ReadingVisualEvidenceStatus,
)
from projectkoios.ingestion.transcript.reading.evidence.stream.evidence import (
    ReadingTextStreamEvidence,
)
from projectkoios.ingestion.transcript.reading.evidence.stream.inventory import (  # noqa: E501
    ReadingTextStreamEvidenceInventory,
)
from projectkoios.ingestion.transcript.reading.evidence.stream.kind import (
    ReadingTextStreamKind,
)
from projectkoios.ingestion.transcript.reading.evidence.stream.selection.basis import (  # noqa: E501
    ReadingTextSelectionBasis,
)
from projectkoios.ingestion.transcript.reading.evidence.stream.selection.definition import (  # noqa: E501
    ReadingTextSelection,
)


@dataclass(frozen=True, slots=True)
class ReadingEvidenceFoundationFixture:
    """Build exact synthetic values shared by reading-evidence fixtures.

    Attributes
    ----------
    digest
        Lowercase synthetic SHA-256 used for managed artifact references.
    """

    digest: SHA256Hash = SHA256Hash("a" * 64)

    def identity(
        self,
        kind: ReadingEvidenceIdentityKind,
        token: str,
    ) -> ReadingEvidenceIdentity:
        """Return one explicit typed synthetic identity.

        Parameters
        ----------
        kind
            Required Ingestion identity role.
        token
            Human-readable synthetic discriminator within that role.

        Returns
        -------
        ReadingEvidenceIdentity
            Typed identity with no filesystem or private-source locator.
        """

        return ReadingEvidenceIdentity(kind=kind, value=f"{kind.value}:{token}")

    def page(self, index: int = 0) -> ReadingPageLocation:
        """Return one canonical physical and printed page location.

        Parameters
        ----------
        index
            Zero-based physical page index.

        Returns
        -------
        ReadingPageLocation
            Location whose printed label is the corresponding positive number.
        """

        return ReadingPageLocation(
            physical_page_index=index,
            printed_page_label=str(index + 1),
        )

    def artifact(
        self,
        *,
        media_type: ManagedArtifactMediaType = (
            ManagedArtifactMediaType.IMAGE_PNG
        ),
    ) -> ManagedArtifactReference:
        """Return one exact bounded managed artifact reference.

        Parameters
        ----------
        media_type
            Closed media type assigned to the synthetic artifact.

        Returns
        -------
        ManagedArtifactReference
            Content-addressed reference with no storage locator or payload.
        """

        return ManagedArtifactReference(
            sha256=self.digest,
            byte_length=128,
            media_type=media_type,
        )

    def artifact_inventory(self) -> ManagedArtifactReferenceInventory:
        """Return a nonempty inventory containing the synthetic artifact.

        Returns
        -------
        ManagedArtifactReferenceInventory
            Exact one-member managed artifact inventory.
        """

        return ManagedArtifactReferenceInventory(self.artifact())

    def native_streams(
        self,
        *,
        page: ReadingPageLocation | None = None,
    ) -> ReadingTextStreamEvidenceInventory:
        """Return exact native-only text stream evidence.

        Parameters
        ----------
        page
            Optional explicit page; page zero is used when omitted.

        Returns
        -------
        ReadingTextStreamEvidenceInventory
            One unreviewed automated native stream.
        """

        location = self.page() if page is None else page
        # Keep acceptance false and review explicit: synthetic evidence should
        # not imply a human decision merely because it is structurally valid.
        native = ReadingTextStreamEvidence(
            kind=ReadingTextStreamKind.NATIVE,
            page_location=location,
            text="Native page text.",
            upstream_id=self.identity(
                ReadingEvidenceIdentityKind.EXTRACTION_RESULT, "native"
            ),
            producer_id=self.identity(
                ReadingEvidenceIdentityKind.PRODUCER, "native"
            ),
            composition_id=None,
            automated=True,
            accepted=False,
            review_status=ReadingReviewStatus.UNREVIEWED,
        )
        return ReadingTextStreamEvidenceInventory(native)

    def native_selection(
        self,
        streams: ReadingTextStreamEvidenceInventory,
    ) -> ReadingTextSelection:
        """Select the exact native stream without fallback.

        Parameters
        ----------
        streams
            Inventory whose first and only member is selected.

        Returns
        -------
        ReadingTextSelection
            Selection using the explicit ``NATIVE_EXACT`` basis.
        """

        native = next(iter(streams))
        return ReadingTextSelection(
            streams=streams,
            selected_stream_id=native.stream_id,
            basis=ReadingTextSelectionBasis.NATIVE_EXACT,
        )

    def text_source_spans(
        self,
        *,
        page: ReadingPageLocation | None = None,
    ) -> ReadingSourceSpanEvidenceInventory:
        """Return one exact character span for clean text evidence.

        Parameters
        ----------
        page
            Optional explicit page; page zero is used when omitted.

        Returns
        -------
        ReadingSourceSpanEvidenceInventory
            One source span covering the synthetic text offsets.
        """

        location = self.page() if page is None else page
        span = ReadingSourceSpanEvidence(
            source_id=self.identity(ReadingEvidenceIdentityKind.SOURCE, "book"),
            page_location=location,
            start_offset=0,
            end_offset=12,
        )
        return ReadingSourceSpanEvidenceInventory(span)

    def source_spans(
        self,
        *,
        source_object_id: ReadingEvidenceIdentity,
        page: ReadingPageLocation | None = None,
    ) -> ReadingSourceSpanEvidenceInventory:
        """Return one bounded visual-object source span.

        Parameters
        ----------
        source_object_id
            Typed identity of the figure, table, or equation object.
        page
            Optional explicit page; page zero is used when omitted.

        Returns
        -------
        ReadingSourceSpanEvidenceInventory
            One span with normalized synthetic bounding-box geometry.
        """

        location = self.page() if page is None else page
        span = ReadingSourceSpanEvidence(
            source_id=self.identity(ReadingEvidenceIdentityKind.SOURCE, "book"),
            page_location=location,
            source_object_id=source_object_id,
            bounding_box=ReadingBoundingBox(0.1, 0.2, 0.3, 0.4),
        )
        return ReadingSourceSpanEvidenceInventory(span)

    def associations(
        self,
        *,
        page: ReadingPageLocation | None = None,
    ) -> ReadingAssociationEvidenceInventory:
        """Return one exact synthetic caption association.

        Parameters
        ----------
        page
            Optional explicit page; page zero is used when omitted.

        Returns
        -------
        ReadingAssociationEvidenceInventory
            One caption association linked to exact source evidence.
        """

        location = self.page() if page is None else page
        # Association identity, referenced block identity, and object identity
        # remain distinct typed roles even in this deliberately small fixture.
        source_object_id = self.identity(
            ReadingEvidenceIdentityKind.SOURCE_OBJECT, "caption"
        )
        span = ReadingSourceSpanEvidence(
            source_id=self.identity(ReadingEvidenceIdentityKind.SOURCE, "book"),
            page_location=location,
            source_object_id=source_object_id,
            start_offset=0,
            end_offset=12,
        )
        association = ReadingAssociationEvidence(
            role=ReadingAssociationRole.CAPTION,
            text="Figure title",
            source_block_ids=ReadingEvidenceIdentityInventory(
                ReadingEvidenceIdentityKind.SOURCE_BLOCK,
                self.identity(
                    ReadingEvidenceIdentityKind.SOURCE_BLOCK, "caption"
                ),
            ),
            source_spans=ReadingSourceSpanEvidenceInventory(span),
            producer_association_id=self.identity(
                ReadingEvidenceIdentityKind.ASSOCIATION, "caption"
            ),
        )
        return ReadingAssociationEvidenceInventory(association)

    def labels(self) -> ReadingSourceLabelInventory:
        """Return one canonical synthetic visual label.

        Returns
        -------
        ReadingSourceLabelInventory
            One-member label inventory containing ``Figure 1``.
        """

        return ReadingSourceLabelInventory("Figure 1")

    def producer_lineage(
        self,
        *,
        source_object_id: ReadingEvidenceIdentity,
        page: ReadingPageLocation | None = None,
        source_spans: ReadingSourceSpanEvidenceInventory | None = None,
        warning_ids: ReadingEvidenceIdentityInventory | None = None,
        producer_token: str = "visual",
    ) -> ReadingProducerLineage:
        """Return exact shared producer lineage for one visual object.

        Parameters
        ----------
        source_object_id
            Typed identity of the visual object.
        page
            Optional explicit page; page zero is used when omitted.
        source_spans
            Optional exact spans; deterministic synthetic geometry is the
            default.
        warning_ids
            Optional warning identities; the default inventory is empty.
        producer_token
            Synthetic token distinguishing the responsible producer.

        Returns
        -------
        ReadingProducerLineage
            Internally consistent lineage with one managed artifact.
        """

        location = self.page() if page is None else page
        # Resolve defaults before construction so every optional override still
        # flows through the same strongly typed lineage boundary.
        return ReadingProducerLineage(
            source_object_id=source_object_id,
            page_location=location,
            source_labels=self.labels(),
            source_spans=(
                self.source_spans(
                    source_object_id=source_object_id,
                    page=location,
                )
                if source_spans is None
                else source_spans
            ),
            warning_ids=(
                self.warning_ids() if warning_ids is None else warning_ids
            ),
            artifacts=self.artifact_inventory(),
            producer_id=self.identity(
                ReadingEvidenceIdentityKind.PRODUCER, producer_token
            ),
            producer_version="1",
        )

    def visual_assessment(
        self,
        *,
        page: ReadingPageLocation | None = None,
        confidence: float = 0.9,
        visual_status: ReadingVisualEvidenceStatus = (
            ReadingVisualEvidenceStatus.PROPOSED
        ),
        review_status: ReadingReviewStatus = ReadingReviewStatus.UNREVIEWED,
    ) -> ReadingVisualAssessment:
        """Return exact shared visual assessment evidence.

        Parameters
        ----------
        page
            Optional explicit page; page zero is used when omitted.
        confidence
            Synthetic detector confidence retained without reinterpretation.
        visual_status
            Typed visual-evidence lifecycle state.
        review_status
            Typed human-review state.

        Returns
        -------
        ReadingVisualAssessment
            Assessment containing the deterministic caption association.
        """

        location = self.page() if page is None else page
        return ReadingVisualAssessment(
            associations=self.associations(page=location),
            confidence=confidence,
            visual_status=visual_status,
            review_status=review_status,
        )

    def warning_ids(self) -> ReadingEvidenceIdentityInventory:
        """Return an empty typed warning identity inventory.

        Returns
        -------
        ReadingEvidenceIdentityInventory
            Empty inventory whose required identity role is ``WARNING``.
        """

        return ReadingEvidenceIdentityInventory(
            ReadingEvidenceIdentityKind.WARNING
        )

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from projectkoios.chunking import TextChunk


@dataclass(frozen=True)
class ChunkSearchResult:
    chunk: TextChunk
    score: float


class UnsupportedRetrievalPurposeError(ValueError):
    """Raised when an admission policy does not authorize a purpose."""


class RetrievalPurpose(StrEnum):
    PROBLEM_SOLVING = "problem_solving"
    LECTURE_AUTHORING = "lecture_authoring"
    CITATION_EVIDENCE = "citation_evidence"
    ORDINARY_RAG = "ordinary_rag"
    LITERATURE_REVIEW = "literature_review"


class CorpusRole(StrEnum):
    THEORY_EVIDENCE = "theory_evidence"
    SOURCE_WORKED_EXAMPLE = "source_worked_example"
    SOURCE_SOLUTION = "source_solution"
    PROBLEM_MATERIAL = "problem_material"
    GENERATED_SOLUTION = "generated_solution"
    REVIEWED_SOLUTION = "reviewed_solution"


@dataclass(frozen=True)
class PurposeAdmission:
    purpose: RetrievalPurpose
    admitted_roles: tuple[CorpusRole, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.purpose, RetrievalPurpose):
            raise ValueError("admission purpose must be explicit")
        if not self.admitted_roles:
            raise ValueError("admission must contain at least one corpus role")
        if len(set(self.admitted_roles)) != len(self.admitted_roles):
            raise ValueError("admitted corpus roles must be unique")
        if any(
            not isinstance(role, CorpusRole) for role in self.admitted_roles
        ):
            raise ValueError("admitted corpus roles must be explicit")


@dataclass(frozen=True)
class RoleAdmissionPolicy:
    admissions: tuple[PurposeAdmission, ...]

    def __post_init__(self) -> None:
        if not self.admissions:
            raise ValueError("admission policy must not be empty")
        if any(
            not isinstance(admission, PurposeAdmission)
            for admission in self.admissions
        ):
            raise ValueError("admission policy entries must be explicit")
        purposes = tuple(item.purpose for item in self.admissions)
        if len(set(purposes)) != len(purposes):
            raise ValueError("admission purposes must be unique")

    def admitted_roles_for(
        self,
        purpose: RetrievalPurpose,
    ) -> tuple[CorpusRole, ...]:
        for admission in self.admissions:
            if admission.purpose is purpose:
                return admission.admitted_roles
        raise UnsupportedRetrievalPurposeError(
            f"unsupported retrieval purpose: {purpose}"
        )


def course_material_admission_policy() -> RoleAdmissionPolicy:
    """Return the explicit admission matrix for course materials."""

    theory_only = (CorpusRole.THEORY_EVIDENCE,)
    return RoleAdmissionPolicy(
        admissions=(
            PurposeAdmission(
                RetrievalPurpose.PROBLEM_SOLVING,
                theory_only,
            ),
            PurposeAdmission(
                RetrievalPurpose.LECTURE_AUTHORING,
                (
                    CorpusRole.THEORY_EVIDENCE,
                    CorpusRole.SOURCE_WORKED_EXAMPLE,
                    CorpusRole.REVIEWED_SOLUTION,
                ),
            ),
            PurposeAdmission(
                RetrievalPurpose.CITATION_EVIDENCE,
                theory_only,
            ),
            PurposeAdmission(
                RetrievalPurpose.ORDINARY_RAG,
                theory_only,
            ),
        )
    )


@dataclass(frozen=True)
class RoleScopedChunk:
    record_id: str
    chunk: TextChunk
    corpus_role: CorpusRole
    admitted_purposes: tuple[RetrievalPurpose, ...]

    def __post_init__(self) -> None:
        if not self.record_id:
            raise ValueError("record_id must be non-empty")
        if not isinstance(self.corpus_role, CorpusRole):
            raise ValueError("corpus role must be explicit")
        if len(set(self.admitted_purposes)) != len(
            self.admitted_purposes
        ):
            raise ValueError("admitted retrieval purposes must be unique")
        if any(
            not isinstance(purpose, RetrievalPurpose)
            for purpose in self.admitted_purposes
        ):
            raise ValueError("admitted retrieval purposes must be explicit")


@dataclass(frozen=True)
class RoleScopedSearchRequest:
    query: str
    purpose: RetrievalPurpose
    excluded_record_ids: tuple[str, ...]
    limit: int

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("query must be non-empty")
        if not isinstance(self.purpose, RetrievalPurpose):
            raise ValueError("retrieval purpose must be explicit")
        if len(set(self.excluded_record_ids)) != len(self.excluded_record_ids):
            raise ValueError("excluded record identities must be unique")
        if self.limit < 1:
            raise ValueError("limit must be positive")


@dataclass(frozen=True)
class RoleScopedChunkSearchResult:
    record: RoleScopedChunk
    score: float
    rank: int

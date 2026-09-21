from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from projectkoios.chunking import TextChunk


@dataclass(frozen=True)
class ChunkSearchResult:
    chunk: TextChunk
    score: float


class CorpusRole(StrEnum):
    EVIDENCE = "evidence"
    PROBLEM_MATERIAL = "problem_material"
    GENERATED_SOLUTION = "generated_solution"
    REVIEWED_SOLUTION = "reviewed_solution"


@dataclass(frozen=True)
class RoleScopedChunk:
    record_id: str
    chunk: TextChunk
    corpus_role: CorpusRole

    def __post_init__(self) -> None:
        if not self.record_id:
            raise ValueError("record_id must be non-empty")


@dataclass(frozen=True)
class RoleScopedSearchRequest:
    query: str
    allowed_roles: tuple[CorpusRole, ...]
    excluded_record_ids: tuple[str, ...]
    limit: int

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("query must be non-empty")
        if not self.allowed_roles:
            raise ValueError("at least one corpus role must be allowed")
        if len(set(self.allowed_roles)) != len(self.allowed_roles):
            raise ValueError("allowed corpus roles must be unique")
        if len(set(self.excluded_record_ids)) != len(self.excluded_record_ids):
            raise ValueError("excluded record identities must be unique")
        if self.limit < 1:
            raise ValueError("limit must be positive")


@dataclass(frozen=True)
class RoleScopedChunkSearchResult:
    record: RoleScopedChunk
    score: float
    rank: int

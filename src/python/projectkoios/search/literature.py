from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from projectkoios.search.models import RetrievalPurpose

_QUERY_TERM = re.compile(r"[^\W_]+", re.UNICODE)


class EvidenceCorpusRole(StrEnum):
    REFERENCE = "reference"


@dataclass(frozen=True)
class EvidencePassage:
    passage_id: str
    source_id: str
    source_sha256: str
    citation_key: str | None
    bibtex_entry_present: bool
    physical_page: int
    printed_page: str | None
    text: str


@dataclass(frozen=True)
class EvidenceSearchResult:
    passage: EvidencePassage
    score: float
    rank: int


@dataclass(frozen=True)
class EvidenceSearchRequest:
    query: str
    purpose: RetrievalPurpose
    corpus_role: EvidenceCorpusRole
    limit: int

    def __post_init__(self) -> None:
        if not self.query.strip() or len(self.query) > 2_000:
            raise ValueError("query must contain 1 to 2000 characters")
        if isinstance(self.limit, bool) or not 1 <= self.limit <= 100:
            raise ValueError("limit must be in [1, 100]")


class PurposeScopedEvidenceIndex(Protocol):
    def search(
        self, request: EvidenceSearchRequest
    ) -> tuple[EvidenceSearchResult, ...]: ...


@dataclass(frozen=True)
class LiteratureClaimQuery:
    claim_id: str
    queries: tuple[str, ...]
    purpose: RetrievalPurpose = RetrievalPurpose.LITERATURE_REVIEW

    def __post_init__(self) -> None:
        if not self.claim_id.strip():
            raise ValueError("claim identity must be nonempty")
        if not self.queries or len(self.queries) > 8:
            raise ValueError("a claim requires 1 to 8 queries")
        if any(
            not query.strip() or len(query) > 2_000 for query in self.queries
        ):
            raise ValueError("each query must contain 1 to 2000 characters")
        if len(set(self.queries)) != len(self.queries):
            raise ValueError("claim queries must be unique")


@dataclass(frozen=True)
class LiteratureEvidenceItem:
    label: str
    query: str
    passage: EvidencePassage
    score: float


@dataclass(frozen=True)
class LiteratureEvidenceBundle:
    claim_id: str
    purpose: RetrievalPurpose
    corpus_role: EvidenceCorpusRole
    evidence: tuple[LiteratureEvidenceItem, ...]


class LiteratureEvidenceBundleService:
    def __init__(self, index: PurposeScopedEvidenceIndex) -> None:
        self.index = index

    def build(
        self,
        claim: LiteratureClaimQuery,
        *,
        per_query_limit: int = 6,
        total_limit: int = 10,
        per_source_limit: int = 2,
    ) -> LiteratureEvidenceBundle:
        if claim.purpose is not RetrievalPurpose.LITERATURE_REVIEW:
            raise ValueError("literature retrieval purpose is required")
        if not 1 <= per_query_limit <= 12:
            raise ValueError("per-query limit must be in [1, 12]")
        if not 1 <= total_limit <= 12:
            raise ValueError("total limit must be in [1, 12]")
        if not 1 <= per_source_limit <= 2:
            raise ValueError("per-source limit must be in [1, 2]")
        selected: list[tuple[str, EvidenceSearchResult]] = []
        passage_ids: set[str] = set()
        source_counts: dict[str, int] = {}
        for query in claim.queries:
            request = EvidenceSearchRequest(
                query=query,
                purpose=claim.purpose,
                corpus_role=EvidenceCorpusRole.REFERENCE,
                limit=per_query_limit,
            )
            for result in self.index.search(request):
                passage = result.passage
                if passage.passage_id in passage_ids:
                    continue
                if source_counts.get(passage.source_id, 0) >= per_source_limit:
                    continue
                passage_ids.add(passage.passage_id)
                source_counts[passage.source_id] = (
                    source_counts.get(passage.source_id, 0) + 1
                )
                selected.append((query, result))
                if len(selected) == total_limit:
                    break
            if len(selected) == total_limit:
                break
        return LiteratureEvidenceBundle(
            claim_id=claim.claim_id,
            purpose=claim.purpose,
            corpus_role=EvidenceCorpusRole.REFERENCE,
            evidence=tuple(
                LiteratureEvidenceItem(
                    label=f"E{rank}",
                    query=query,
                    passage=result.passage,
                    score=result.score,
                )
                for rank, (query, result) in enumerate(selected, start=1)
            ),
        )


class SqliteFtsReferenceEvidenceIndex:
    """Read-only adapter for the demonstrated local RAG schema."""

    def __init__(self, database: Path) -> None:
        candidate = database.expanduser()
        if candidate.is_symlink():
            raise ValueError("database must not be a symlink")
        resolved = candidate.resolve(strict=True)
        if not resolved.is_file():
            raise ValueError("database must be a regular file")
        self.database = resolved
        self._validate_schema()

    def search(
        self, request: EvidenceSearchRequest
    ) -> tuple[EvidenceSearchResult, ...]:
        if request.purpose is not RetrievalPurpose.LITERATURE_REVIEW:
            raise ValueError("unsupported retrieval purpose")
        if request.corpus_role is not EvidenceCorpusRole.REFERENCE:
            raise ValueError("literature retrieval is reference-only")
        expression = _fts_expression(request.query)
        if not expression:
            return ()
        expanded_limit = max(request.limit, min(500, request.limit * 10))
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    p.passage_id,
                    p.source_id,
                    d.source_sha256,
                    p.page_index,
                    p.printed_page_label,
                    p.text,
                    d.citation_key,
                    d.bibtex_entry_present,
                    -bm25(passages_fts) AS score
                FROM passages_fts
                JOIN passages AS p
                    ON p.passage_id = passages_fts.passage_id
                JOIN documents AS d ON d.source_id = p.source_id
                WHERE passages_fts MATCH ?
                    AND d.corpus_role = 'reference'
                ORDER BY bm25(passages_fts), p.passage_id
                LIMIT ?
                """,
                (expression, expanded_limit),
            ).fetchall()
        selected: list[EvidenceSearchResult] = []
        source_ids: set[str] = set()
        for row in rows:
            source_id = str(row[1])
            if source_id in source_ids:
                continue
            source_ids.add(source_id)
            selected.append(
                EvidenceSearchResult(
                    passage=EvidencePassage(
                        passage_id=str(row[0]),
                        source_id=source_id,
                        source_sha256=str(row[2]),
                        citation_key=(None if row[6] is None else str(row[6])),
                        bibtex_entry_present=bool(row[7]),
                        physical_page=int(row[3]) + 1,
                        printed_page=(None if row[4] is None else str(row[4])),
                        text=str(row[5]),
                    ),
                    score=float(row[8]),
                    rank=len(selected) + 1,
                )
            )
            if len(selected) == request.limit:
                break
        return tuple(selected)

    def _connect(self) -> sqlite3.Connection:
        uri = f"file:{self.database.as_posix()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        connection.execute("PRAGMA query_only = ON")
        return connection

    def _validate_schema(self) -> None:
        required = {"documents", "passages", "passages_fts"}
        with closing(self._connect()) as connection:
            existing = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type IN "
                    "('table', 'view')"
                )
            }
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if not required <= existing:
            raise ValueError("database does not provide the local RAG schema")
        if integrity is None or integrity[0] != "ok":
            raise ValueError("database integrity check failed")


def _fts_expression(query: str) -> str:
    terms = tuple(
        dict.fromkeys(term.casefold() for term in _QUERY_TERM.findall(query))
    )
    return " OR ".join(
        f'"{term.replace(chr(34), chr(34) * 2)}"' for term in terms
    )

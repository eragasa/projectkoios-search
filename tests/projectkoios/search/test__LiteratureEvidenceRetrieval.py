from __future__ import annotations

import sqlite3
from pathlib import Path

from projectkoios.search import (
    EvidenceCorpusRole,
    EvidencePassage,
    EvidenceSearchRequest,
    EvidenceSearchResult,
    LiteratureClaimQuery,
    LiteratureEvidenceBundleService,
    RetrievalPurpose,
    SqliteFtsReferenceEvidenceIndex,
)


def _passage(identity: str, source: str) -> EvidencePassage:
    return EvidencePassage(
        passage_id=identity,
        source_id=source,
        source_sha256=source.removeprefix("source:sha256:"),
        citation_key="Example1965",
        bibtex_entry_present=True,
        physical_page=2,
        printed_page=None,
        text=f"evidence {identity}",
    )


class _Index:
    def __init__(self) -> None:
        self.requests: list[EvidenceSearchRequest] = []

    def search(
        self, request: EvidenceSearchRequest
    ) -> tuple[EvidenceSearchResult, ...]:
        self.requests.append(request)
        common = EvidenceSearchResult(
            passage=_passage("p-common", "source:sha256:" + "a" * 64),
            score=9.0,
            rank=1,
        )
        unique = EvidenceSearchResult(
            passage=_passage(
                f"p-{len(self.requests)}", "source:sha256:" + "b" * 64
            ),
            score=8.0,
            rank=2,
        )
        return common, unique


def test__literature_bundle__is_reference_only_and_deduplicated() -> None:
    index = _Index()
    service = LiteratureEvidenceBundleService(index)

    bundle = service.build(
        LiteratureClaimQuery("C-001", ("first query", "second query")),
        total_limit=3,
    )

    assert bundle.purpose is RetrievalPurpose.LITERATURE_REVIEW
    assert bundle.corpus_role is EvidenceCorpusRole.REFERENCE
    assert [item.label for item in bundle.evidence] == ["E1", "E2", "E3"]
    assert len({item.passage.passage_id for item in bundle.evidence}) == 3
    assert all(
        request.corpus_role is EvidenceCorpusRole.REFERENCE
        for request in index.requests
    )
    assert all(
        request.purpose is RetrievalPurpose.LITERATURE_REVIEW
        for request in index.requests
    )


def _database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE documents (
            source_id TEXT PRIMARY KEY,
            source_sha256 TEXT NOT NULL,
            corpus_role TEXT NOT NULL,
            citation_key TEXT,
            bibtex_entry_present INTEGER NOT NULL
        );
        CREATE TABLE passages (
            passage_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            page_index INTEGER NOT NULL,
            printed_page_label TEXT,
            text TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE passages_fts USING fts5(
            passage_id UNINDEXED,
            source_id UNINDEXED,
            text
        );
        """
    )
    rows = (
        ("reference", "reference", "Ref1965", "metal theorem"),
        ("manuscript", "manuscript", None, "metal theorem classifier"),
    )
    for source_id, role, citation_key, text in rows:
        connection.execute(
            "INSERT INTO documents VALUES (?, ?, ?, ?, ?)",
            (source_id, source_id * 8, role, citation_key, 1),
        )
        passage_id = f"passage-{source_id}"
        connection.execute(
            "INSERT INTO passages VALUES (?, ?, 0, NULL, ?)",
            (passage_id, source_id, text),
        )
        connection.execute(
            "INSERT INTO passages_fts VALUES (?, ?, ?)",
            (passage_id, source_id, text),
        )
    connection.commit()
    connection.close()


def test__sqlite_reference_index__cannot_return_manuscript(
    tmp_path: Path,
) -> None:
    database = tmp_path / "index.sqlite3"
    _database(database)
    index = SqliteFtsReferenceEvidenceIndex(database)

    results = index.search(
        EvidenceSearchRequest(
            query="metal classifier",
            purpose=RetrievalPurpose.LITERATURE_REVIEW,
            corpus_role=EvidenceCorpusRole.REFERENCE,
            limit=10,
        )
    )

    assert [result.passage.source_id for result in results] == ["reference"]
    assert results[0].passage.citation_key == "Ref1965"

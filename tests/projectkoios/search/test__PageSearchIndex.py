from __future__ import annotations

import json
import sqlite3
import unicodedata
from pathlib import Path
from typing import cast

import pytest
from projectkoios.search import (
    PageSearchBuildDocument,
    PageSearchBuildPlan,
    PageSearchBuildPlanError,
    PageSearchIndex,
    PageSearchIndexUnavailableError,
    PageSearchQueryError,
    build_page_search_index,
)
from projectkoios.search.page_projection_chunking import (
    PageProjectionChunker,
    PageProjectionChunkingRequest,
    PageProjectionChunkingResult,
)
from projectkoios.search.page_search import MAX_CHUNK_CHARS
from projectkoios.search.page_search_cli import main

from tests.projectkoios.search.page_projection_chunking.fixture.result import (
    build_page_projection_result,
)


def _chunking_result() -> PageProjectionChunkingResult:
    return PageProjectionChunker().action(
        request=PageProjectionChunkingRequest(
            projection_result=build_page_projection_result()
        )
    )


def _plan() -> PageSearchBuildPlan:
    return PageSearchBuildPlan(
        documents=(
            PageSearchBuildDocument(
                document_id="doc-01",
                filename="Kittel8ed.pdf",
                title="Introduction to Solid State Physics",
                status_reason="exact typed page projection admitted",
                projection=_chunking_result(),
            ),
            PageSearchBuildDocument(
                document_id="doc-02",
                filename="RudanPhysicsSemiconductors.pdf",
                title="Physics of Semiconductor Devices",
                status_reason="typed page projection pending",
                projection=None,
            ),
        )
    )


def test__builds_typed_page_projection_and_safe_bm25_results(
    tmp_path: Path,
) -> None:
    database = tmp_path / "index" / "search.sqlite3"

    status = build_page_search_index(database=database, plan=_plan())

    assert status.ready
    assert status.schema_version == "2"
    assert status.indexed_document_count == 1
    assert status.indexed_page_count == 1
    assert status.searchable_page_count == 1
    assert status.chunk_count == 1
    assert database.stat().st_mode & 0o777 == 0o600
    assert [document.document_id for document in status.documents] == [
        "doc-01",
        "doc-02",
    ]
    assert status.documents[0].status == "indexed"
    assert status.documents[1].status == "pending"
    assert status.documents[1].source_page_count == 0

    index = PageSearchIndex(database)
    response = index.search("Canonical paragraph")
    assert response.total_hits == 1
    result = response.results[0]
    assert result.document_id == "doc-01"
    assert result.filename == "Kittel8ed.pdf"
    assert result.physical_page == 1
    assert result.printed_page == "1"
    assert result.chunk_ordinal == 1
    assert result.rank == 1
    assert result.bm25_score > 0
    assert "Figure title" in result.snippet
    assert len(result.snippet) <= 600
    assert not any(
        unicodedata.category(character).startswith("C")
        for character in result.snippet
    )
    assert "hash" not in result.__dataclass_fields__
    assert "path" not in result.__dataclass_fields__

    with sqlite3.connect(database) as connection:
        projection_result_id = connection.execute(
            "SELECT projection_result_id FROM documents "
            "WHERE document_id = 'doc-01'"
        ).fetchone()[0]
        text = connection.execute("SELECT text FROM chunks").fetchone()[0]
    assert projection_result_id.startswith("page-projection-result:sha256:")
    assert len(text) <= MAX_CHUNK_CHARS


def test__search_is_bounded(tmp_path: Path) -> None:
    database = tmp_path / "search.sqlite3"
    build_page_search_index(database=database, plan=_plan())
    index = PageSearchIndex(database)

    response = index.search("Canonical", limit=1)
    assert response.total_hits == 1
    assert response.next_offset is None

    for query, limit, offset in (
        ("", 10, 0),
        ("word " * 17, 10, 0),
        ("valid", 0, 0),
        ("valid", 51, 0),
        ("valid", 10, -1),
        ("unsafe\u0002query", 10, 0),
        ("valid", 10, 1001),
    ):
        with pytest.raises(PageSearchQueryError):
            index.search(query, limit=limit, offset=offset)


def test__build_plan_rejects_untyped_or_misordered_inputs() -> None:
    untyped = PageSearchBuildDocument(
        document_id="doc-01",
        filename="one.pdf",
        title="One",
        status_reason="invalid runtime input",
        projection=cast(PageProjectionChunkingResult, object()),
    )
    with pytest.raises(PageSearchBuildPlanError, match="unsupported type"):
        PageSearchBuildPlan(documents=(untyped,))

    pending_one = PageSearchBuildDocument(
        document_id="doc-02",
        filename="two.pdf",
        title="Two",
        status_reason="pending",
        projection=None,
    )
    pending_two = PageSearchBuildDocument(
        document_id="doc-01",
        filename="one.pdf",
        title="One",
        status_reason="pending",
        projection=None,
    )
    with pytest.raises(PageSearchBuildPlanError, match="document order"):
        PageSearchBuildPlan(documents=(pending_one, pending_two))


def test__builder_revalidates_plan_freshness(tmp_path: Path) -> None:
    plan = _plan()
    with pytest.raises(AttributeError):
        plan._documents = ()  # type: ignore[misc]

    object.__setattr__(plan, "_documents", ())
    with pytest.raises(PageSearchBuildPlanError, match="stale or invalid"):
        build_page_search_index(
            database=tmp_path / "search.sqlite3",
            plan=plan,
        )


def test__failed_rebuild_preserves_live_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "search.sqlite3"
    build_page_search_index(database=database, plan=_plan())
    original = database.read_bytes()

    def fail_write(*args: object, **kwargs: object) -> None:
        raise RuntimeError("injected write failure")

    monkeypatch.setattr(
        "projectkoios.search.page_search._write_index",
        fail_write,
    )
    with pytest.raises(RuntimeError, match="injected write failure"):
        build_page_search_index(database=database, plan=_plan())

    assert database.read_bytes() == original
    assert PageSearchIndex(database).search("Canonical").total_hits == 1
    assert not tuple(database.parent.glob(".search.sqlite3.*.tmp"))


def test__reader_fails_closed_for_missing_foreign_or_inconsistent_database(
    tmp_path: Path,
) -> None:
    with pytest.raises(PageSearchIndexUnavailableError):
        PageSearchIndex(tmp_path / "missing.sqlite3")

    foreign = tmp_path / "foreign.sqlite3"
    sqlite3.connect(foreign).close()
    with pytest.raises(PageSearchIndexUnavailableError):
        PageSearchIndex(foreign)

    database = tmp_path / "search.sqlite3"
    build_page_search_index(database=database, plan=_plan())
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE documents SET chunk_count = 2 WHERE document_id = 'doc-01'"
        )
    with pytest.raises(PageSearchIndexUnavailableError):
        PageSearchIndex(database)

    build_page_search_index(database=database, plan=_plan())
    existing_reader = PageSearchIndex(database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE documents SET title = ? WHERE document_id = 'doc-01'",
            ("unsafe\u0002title",),
        )
    with pytest.raises(PageSearchIndexUnavailableError):
        existing_reader.status()

    build_page_search_index(database=database, plan=_plan())
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE chunks SET printed_page = 'substituted'")
    with pytest.raises(PageSearchIndexUnavailableError):
        PageSearchIndex(database)


def test__cli_emits_safe_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = tmp_path / "search.sqlite3"
    build_page_search_index(database=database, plan=_plan())

    assert (
        main(
            [
                "query",
                "--database",
                str(database),
                "--query",
                "Canonical paragraph",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["total_hits"] == 1
    result = payload["results"][0]
    assert result["document_id"] == "doc-01"
    assert result["filename"] == "Kittel8ed.pdf"
    assert not any("hash" in key or "path" in key for key in result)

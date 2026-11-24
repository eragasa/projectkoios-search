from __future__ import annotations

import os
import re
import sqlite3
import tempfile
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Literal, cast

if TYPE_CHECKING:
    from projectkoios.search.page_projection_chunking import (
        PageProjectionChunkingResult,
    )

SCHEMA_VERSION: Final = "2"
LEGACY_SCHEMA_VERSION: Final = "1"
BUILD_PLAN_CONTRACT_VERSION: Final = "1.0"
SLICE_ID: Final = "solid-state-semiconductor-v1"
MAX_CHUNK_CHARS: Final = 5_000
MAX_QUERY_CHARS: Final = 256
MAX_QUERY_TERMS: Final = 16
MAX_LIMIT: Final = 50
MAX_OFFSET: Final = 1_000
MAX_SNIPPET_CHARS: Final = 600
MAX_DOCUMENTS: Final = 100
MAX_TOTAL_PAGES: Final = 1_000_000
MAX_TOTAL_PROJECTED_BLOCKS: Final = 1_000_000
MAX_FILENAME_CHARS: Final = 1_024
MAX_STATUS_REASON_CHARS: Final = 4_096
MAX_PRINTED_PAGE_CHARS: Final = 1_024

_DOCUMENT_STATUS = Literal["indexed", "excluded", "pending"]
_RESOLVED_STATUS = Literal["indexed", "pending"]
_QUERY_TERM = re.compile(r"[^\W_]+(?:[-'][^\W_]+)*", re.UNICODE)
_PROJECTION_RESULT_ID = re.compile(
    r"page-projection-result:sha256:[0-9a-f]{64}"
)


class PageSearchError(Exception):
    """Base error for the page-search operation."""


class PageSearchIndexUnavailableError(PageSearchError):
    """Raised when a readable, compatible page-search index is unavailable."""


class PageSearchQueryError(PageSearchError, ValueError):
    """Raised when a search request is outside the public query bounds."""


class PageSearchBuildPlanError(PageSearchError, ValueError):
    """Raised when an owner-resolved build plan is inconsistent."""


@dataclass(frozen=True, slots=True)
class PageSearchDocument:
    """Safe document coverage metadata exposed to API consumers."""

    document_id: str
    filename: str
    title: str
    status: _DOCUMENT_STATUS
    status_reason: str
    source_page_count: int
    source_paragraph_count: int
    indexed_page_count: int
    searchable_page_count: int
    chunk_count: int


@dataclass(frozen=True, slots=True)
class PageSearchIndexStatus:
    """Readiness and source coverage for one immutable index generation."""

    slice_id: str
    schema_version: str
    ready: bool
    documents: tuple[PageSearchDocument, ...]
    indexed_document_count: int
    indexed_page_count: int
    searchable_page_count: int
    chunk_count: int


@dataclass(frozen=True, slots=True)
class PageSearchResult:
    """One bounded BM25-ranked page-chunk result with a safe citation."""

    rank: int
    chunk_id: str
    document_id: str
    filename: str
    title: str
    physical_page: int
    printed_page: str | None
    chunk_ordinal: int
    snippet: str
    bm25_score: float


@dataclass(frozen=True, slots=True)
class PageSearchResponse:
    """A bounded page of stable BM25-ranked search results."""

    query: str
    limit: int
    offset: int
    total_hits: int
    next_offset: int | None
    results: tuple[PageSearchResult, ...]


@dataclass(frozen=True, slots=True)
class PageSearchBuildDocument:
    """Bind catalog-safe metadata to an exact typed page projection."""

    document_id: str
    filename: str
    title: str
    status_reason: str
    projection: PageProjectionChunkingResult | None


@dataclass(frozen=True, slots=True)
class _ResolvedPage:
    physical_page: int
    printed_page: str | None
    text_units: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _ResolvedDocument:
    document_id: str
    filename: str
    title: str
    status: _RESOLVED_STATUS
    status_reason: str
    projection_result_id: str | None
    source_page_count: int
    source_paragraph_count: int
    pages: tuple[_ResolvedPage, ...]


@dataclass(frozen=True, slots=True)
class _Chunk:
    chunk_id: str
    document_id: str
    physical_page: int
    printed_page: str | None
    chunk_ordinal: int
    text: str


@dataclass(frozen=True, slots=True, init=False)
class PageSearchBuildPlan:
    """Validate and retain one immutable typed-projection build roster."""

    _contract_version: str
    _documents: tuple[_ResolvedDocument, ...]
    _inputs: tuple[PageSearchBuildDocument, ...]
    _slice_id: str

    def __init__(
        self,
        *,
        documents: Sequence[PageSearchBuildDocument],
        contract_version: str = BUILD_PLAN_CONTRACT_VERSION,
        slice_id: str = SLICE_ID,
    ) -> None:
        if contract_version != BUILD_PLAN_CONTRACT_VERSION:
            raise PageSearchBuildPlanError(
                "page-search build plan contract is unsupported"
            )
        if slice_id != SLICE_ID:
            raise PageSearchBuildPlanError("page-search slice is unsupported")
        inputs = tuple(documents)
        if not inputs or len(inputs) > MAX_DOCUMENTS:
            raise PageSearchBuildPlanError(
                "page-search roster count is outside its supported bound"
            )
        if any(
            type(document) is not PageSearchBuildDocument for document in inputs
        ):
            raise PageSearchBuildPlanError(
                "page-search roster contains an unsupported document"
            )
        resolved = tuple(
            _resolve_build_document(document) for document in inputs
        )
        if tuple(document.document_id for document in resolved) != tuple(
            sorted(document.document_id for document in resolved)
        ):
            raise PageSearchBuildPlanError(
                "page-search roster is not in document order"
            )
        if len({document.document_id for document in resolved}) != len(
            resolved
        ):
            raise PageSearchBuildPlanError(
                "page-search document IDs are duplicated"
            )
        if len({document.filename for document in resolved}) != len(resolved):
            raise PageSearchBuildPlanError(
                "page-search filenames are duplicated"
            )
        if (
            sum(document.source_page_count for document in resolved)
            > MAX_TOTAL_PAGES
        ):
            raise PageSearchBuildPlanError(
                "page-search page count exceeds its supported bound"
            )
        if (
            sum(
                len(page.text_units)
                for document in resolved
                for page in document.pages
            )
            > MAX_TOTAL_PROJECTED_BLOCKS
        ):
            raise PageSearchBuildPlanError(
                "page-search block count exceeds its supported bound"
            )
        result_ids = tuple(
            document.projection_result_id
            for document in resolved
            if document.projection_result_id is not None
        )
        if len(result_ids) != len(set(result_ids)):
            raise PageSearchBuildPlanError(
                "page-search projections are duplicated"
            )
        for document in resolved:
            _validate_resolved_document(document)
        object.__setattr__(self, "_contract_version", contract_version)
        object.__setattr__(self, "_slice_id", slice_id)
        object.__setattr__(self, "_inputs", inputs)
        object.__setattr__(self, "_documents", resolved)

    @property
    def contract_version(self) -> str:
        """Return the runtime build-plan contract version."""
        return self._contract_version

    @property
    def slice_id(self) -> str:
        """Return the index slice identifier."""
        return self._slice_id

    @property
    def document_count(self) -> int:
        """Return the resolved roster size without exposing source evidence."""
        return len(self._documents)


def _resolve_build_document(
    document: PageSearchBuildDocument,
) -> _ResolvedDocument:
    from projectkoios.search.page_projection_chunking import (
        PageProjectionChunkingResult,
        PageProjectionChunkStyle,
    )

    projection = document.projection
    if projection is None:
        return _ResolvedDocument(
            document_id=document.document_id,
            filename=document.filename,
            title=document.title,
            status="pending",
            status_reason=document.status_reason,
            projection_result_id=None,
            source_page_count=0,
            source_paragraph_count=0,
            pages=(),
        )
    if type(projection) is not PageProjectionChunkingResult:
        raise PageSearchBuildPlanError(
            "indexed page-search projection has an unsupported type"
        )
    projected_pages = projection.projected_pages
    chunks_by_page: dict[int, list[str]] = {
        page.physical_page_index: [] for page in projected_pages
    }
    for chunk in projection.chunks:
        try:
            chunks_by_page[chunk.physical_page_index].append(chunk.text)
        except KeyError as error:
            raise PageSearchBuildPlanError(
                "page-search chunks reference an absent physical page"
            ) from error
    pages = tuple(
        _ResolvedPage(
            physical_page=page.physical_page_number,
            printed_page=page.printed_page_label,
            text_units=tuple(chunks_by_page[page.physical_page_index]),
        )
        for page in projected_pages
    )
    paragraph_count = sum(
        chunk.style is PageProjectionChunkStyle.PARAGRAPH
        for chunk in projection.chunks
    )
    return _ResolvedDocument(
        document_id=document.document_id,
        filename=document.filename,
        title=document.title,
        status="indexed",
        status_reason=document.status_reason,
        projection_result_id=projection.chunks.page_projection_result_id,
        source_page_count=len(pages),
        source_paragraph_count=paragraph_count,
        pages=pages,
    )


def _validate_resolved_document(document: _ResolvedDocument) -> None:
    if (
        not document.document_id
        or len(document.document_id) > 512
        or _contains_control(document.document_id)
    ):
        raise PageSearchBuildPlanError("page-search document ID is invalid")
    if (
        not document.filename
        or len(document.filename) > MAX_FILENAME_CHARS
        or document.filename != Path(document.filename).name
        or "/" in document.filename
        or "\\" in document.filename
        or _contains_control(document.filename)
    ):
        raise PageSearchBuildPlanError("page-search filename is invalid")
    if (
        not document.title
        or len(document.title) > 16_384
        or _contains_control(document.title)
    ):
        raise PageSearchBuildPlanError("page-search title is invalid")
    if (
        not document.status_reason
        or len(document.status_reason) > MAX_STATUS_REASON_CHARS
        or _contains_control(document.status_reason)
    ):
        raise PageSearchBuildPlanError("page-search status reason is invalid")
    if document.status == "pending":
        if (
            document.projection_result_id is not None
            or document.source_page_count != 0
            or document.source_paragraph_count != 0
            or document.pages
        ):
            raise PageSearchBuildPlanError(
                "pending page-search document contains a projection"
            )
        return
    if document.status != "indexed":
        raise PageSearchBuildPlanError("page-search document status is invalid")
    if (
        document.projection_result_id is None
        or _PROJECTION_RESULT_ID.fullmatch(document.projection_result_id)
        is None
    ):
        raise PageSearchBuildPlanError(
            "indexed page-search document lacks an exact projection"
        )
    if document.source_page_count != len(document.pages) or not document.pages:
        raise PageSearchBuildPlanError(
            "indexed page-search page inventory is inconsistent"
        )
    if document.source_paragraph_count < 0:
        raise PageSearchBuildPlanError(
            "indexed page-search paragraph count is invalid"
        )
    if tuple(page.physical_page for page in document.pages) != tuple(
        range(1, len(document.pages) + 1)
    ):
        raise PageSearchBuildPlanError(
            "indexed page-search pages are not contiguous"
        )
    for page in document.pages:
        if page.printed_page is not None and (
            not page.printed_page.strip()
            or len(page.printed_page) > MAX_PRINTED_PAGE_CHARS
            or _contains_control(page.printed_page)
        ):
            raise PageSearchBuildPlanError(
                "indexed page-search printed page is invalid"
            )
        if any(not isinstance(unit, str) for unit in page.text_units):
            raise PageSearchBuildPlanError(
                "indexed page-search text projection is invalid"
            )


_SCHEMA: Final = """
PRAGMA foreign_keys = ON;
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID;
CREATE TABLE documents (
    document_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('indexed', 'pending')),
    status_reason TEXT NOT NULL,
    projection_result_id TEXT,
    source_page_count INTEGER NOT NULL CHECK (source_page_count >= 0),
    source_paragraph_count INTEGER NOT NULL CHECK (source_paragraph_count >= 0),
    indexed_page_count INTEGER NOT NULL CHECK (indexed_page_count >= 0),
    searchable_page_count INTEGER NOT NULL CHECK (searchable_page_count >= 0),
    chunk_count INTEGER NOT NULL CHECK (chunk_count >= 0),
    CHECK (
        (status = 'indexed' AND projection_result_id IS NOT NULL)
        OR (status = 'pending' AND projection_result_id IS NULL)
    )
) WITHOUT ROWID;
CREATE TABLE pages (
    document_id TEXT NOT NULL REFERENCES documents(document_id),
    physical_page INTEGER NOT NULL CHECK (physical_page > 0),
    printed_page TEXT,
    has_text INTEGER NOT NULL CHECK (has_text IN (0, 1)),
    PRIMARY KEY (document_id, physical_page)
) WITHOUT ROWID;
CREATE TABLE chunks (
    chunk_id TEXT NOT NULL UNIQUE,
    document_id TEXT NOT NULL,
    physical_page INTEGER NOT NULL,
    printed_page TEXT,
    chunk_ordinal INTEGER NOT NULL CHECK (chunk_ordinal > 0),
    text TEXT NOT NULL CHECK (length(text) BETWEEN 1 AND 5000),
    FOREIGN KEY (document_id, physical_page)
        REFERENCES pages(document_id, physical_page),
    UNIQUE (document_id, physical_page, chunk_ordinal)
);
CREATE VIRTUAL TABLE chunks_fts USING fts5(
    text,
    content='chunks',
    content_rowid='rowid',
    tokenize='unicode61 remove_diacritics 2'
);
"""


class PageSearchIndex:
    """Read-only owner operation over a validated page-search index."""

    def __init__(self, database: Path) -> None:
        self._database = Path(database)
        self._validate_index()

    def status(self) -> PageSearchIndexStatus:
        """Return readiness and per-document coverage without private inputs."""
        self._validate_index()
        try:
            with self._connect() as connection:
                metadata = _metadata(connection)
                _validate_schema_and_slice(metadata)
                rows = connection.execute(
                    """
                    SELECT document_id, filename, title, status, status_reason,
                           source_page_count, source_paragraph_count,
                           indexed_page_count, searchable_page_count,
                           chunk_count
                    FROM documents
                    ORDER BY document_id
                    """
                ).fetchall()
        except (sqlite3.Error, KeyError) as error:
            raise PageSearchIndexUnavailableError(
                "page-search index could not be read"
            ) from error

        documents = tuple(_document_from_row(row) for row in rows)
        return PageSearchIndexStatus(
            slice_id=metadata["slice_id"],
            schema_version=metadata["schema_version"],
            ready=True,
            documents=documents,
            indexed_document_count=sum(
                document.status == "indexed" for document in documents
            ),
            indexed_page_count=sum(
                document.indexed_page_count for document in documents
            ),
            searchable_page_count=sum(
                document.searchable_page_count for document in documents
            ),
            chunk_count=sum(document.chunk_count for document in documents),
        )

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        offset: int = 0,
    ) -> PageSearchResponse:
        """Search literal query terms using BM25 with stable tie ordering."""
        normalized, match_expression = _validate_query(query, limit, offset)
        self._validate_index()
        try:
            with self._connect() as connection:
                _validate_schema_and_slice(_metadata(connection))
                total_hits = int(
                    connection.execute(
                        "SELECT count(*) FROM chunks_fts "
                        "WHERE chunks_fts MATCH ?",
                        (match_expression,),
                    ).fetchone()[0]
                )
                rows = connection.execute(
                    """
                    SELECT c.chunk_id, c.document_id, d.filename, d.title,
                           c.physical_page, c.printed_page, c.chunk_ordinal,
                           snippet(chunks_fts, 0, '', '', ' … ', 32),
                           bm25(chunks_fts)
                    FROM chunks_fts
                    JOIN chunks AS c ON c.rowid = chunks_fts.rowid
                    JOIN documents AS d ON d.document_id = c.document_id
                    WHERE chunks_fts MATCH ?
                    ORDER BY bm25(chunks_fts), c.document_id,
                             c.physical_page, c.chunk_ordinal
                    LIMIT ? OFFSET ?
                    """,
                    (match_expression, limit, offset),
                ).fetchall()
        except (sqlite3.Error, KeyError) as error:
            raise PageSearchIndexUnavailableError(
                "page-search query could not be completed"
            ) from error

        results = tuple(
            PageSearchResult(
                rank=offset + position,
                chunk_id=str(row[0]),
                document_id=str(row[1]),
                filename=str(row[2]),
                title=str(row[3]),
                physical_page=int(row[4]),
                printed_page=None if row[5] is None else str(row[5]),
                chunk_ordinal=int(row[6]),
                snippet=_bounded_snippet(str(row[7])),
                bm25_score=-float(row[8]),
            )
            for position, row in enumerate(rows, start=1)
        )
        consumed = offset + len(results)
        next_offset = (
            consumed
            if consumed < total_hits and consumed <= MAX_OFFSET
            else None
        )
        return PageSearchResponse(
            query=normalized,
            limit=limit,
            offset=offset,
            total_hits=total_hits,
            next_offset=next_offset,
            results=results,
        )

    def _connect(self) -> sqlite3.Connection:
        uri = self._database.absolute().as_uri() + "?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=5.0)
        connection.execute("PRAGMA query_only = ON")
        return connection

    def _validate_index(self) -> None:
        if not self._database.is_file():
            raise PageSearchIndexUnavailableError(
                "page-search index does not exist"
            )
        try:
            with self._connect() as connection:
                metadata = _metadata(connection)
                _validate_schema_and_slice(metadata)
                integrity = connection.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0]
                foreign_key_issue = connection.execute(
                    "PRAGMA foreign_key_check"
                ).fetchone()
                document_rows = connection.execute(
                    """
                    SELECT document_id, filename, title, status, status_reason,
                           source_page_count, indexed_page_count,
                           searchable_page_count, chunk_count
                    FROM documents
                    ORDER BY document_id
                    """
                ).fetchall()
                actual_document_counts = connection.execute(
                    """
                    SELECT d.document_id,
                           (SELECT count(*) FROM pages AS p
                            WHERE p.document_id = d.document_id),
                           (SELECT count(*) FROM pages AS p
                            WHERE p.document_id = d.document_id
                              AND p.has_text = 1),
                           (SELECT count(*) FROM chunks AS c
                            WHERE c.document_id = d.document_id)
                    FROM documents AS d
                    ORDER BY d.document_id
                    """
                ).fetchall()
                fts_count = connection.execute(
                    "SELECT count(*) FROM chunks_fts"
                ).fetchone()[0]
                invalid_chunk_page_bindings = connection.execute(
                    """
                    SELECT count(*)
                    FROM chunks AS c
                    JOIN pages AS p
                      ON p.document_id = c.document_id
                     AND p.physical_page = c.physical_page
                    WHERE c.printed_page IS NOT p.printed_page
                    """
                ).fetchone()[0]
                printed_pages = connection.execute(
                    "SELECT printed_page FROM pages "
                    "WHERE printed_page IS NOT NULL"
                ).fetchall()
                chunk_ids = connection.execute(
                    "SELECT chunk_id FROM chunks"
                ).fetchall()
                if metadata["schema_version"] == SCHEMA_VERSION:
                    invalid_bindings = connection.execute(
                        """
                        SELECT count(*) FROM documents
                        WHERE (status = 'indexed'
                               AND projection_result_id IS NULL)
                           OR (status = 'pending'
                               AND projection_result_id IS NOT NULL)
                        """
                    ).fetchone()[0]
                    projection_result_ids = connection.execute(
                        "SELECT projection_result_id FROM documents "
                        "WHERE status = 'indexed'"
                    ).fetchall()
                else:
                    invalid_bindings = 0
                    projection_result_ids = []
        except (sqlite3.Error, KeyError) as error:
            raise PageSearchIndexUnavailableError(
                "page-search index is invalid"
            ) from error
        if (
            integrity != "ok"
            or foreign_key_issue is not None
            or invalid_bindings
            or invalid_chunk_page_bindings
            or any(
                type(row[0]) is not str
                or _PROJECTION_RESULT_ID.fullmatch(row[0]) is None
                for row in projection_result_ids
            )
        ):
            raise PageSearchIndexUnavailableError(
                "page-search index is invalid"
            )
        if not document_rows:
            raise PageSearchIndexUnavailableError(
                "page-search index roster is empty"
            )
        if any(
            type(row[0]) is not str
            or not row[0]
            or len(row[0]) > 512
            or _contains_control(row[0])
            or type(row[1]) is not str
            or not row[1]
            or len(row[1]) > MAX_FILENAME_CHARS
            or row[1] != Path(row[1]).name
            or "/" in row[1]
            or "\\" in row[1]
            or _contains_control(row[1])
            for row in document_rows
        ):
            raise PageSearchIndexUnavailableError(
                "page-search index roster is invalid"
            )
        ids = [row[0] for row in document_rows]
        filenames = [row[1] for row in document_rows]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise PageSearchIndexUnavailableError(
                "page-search index roster is invalid"
            )
        if len(filenames) != len(set(filenames)):
            raise PageSearchIndexUnavailableError(
                "page-search index roster is invalid"
            )
        if any(
            type(row[2]) is not str
            or not row[2]
            or len(row[2]) > 16_384
            or _contains_control(row[2])
            or type(row[4]) is not str
            or not row[4]
            or len(row[4]) > MAX_STATUS_REASON_CHARS
            or _contains_control(row[4])
            for row in document_rows
        ):
            raise PageSearchIndexUnavailableError(
                "page-search index metadata is unsafe"
            )
        actual_counts_by_id = {
            str(row[0]): tuple(int(value) for value in row[1:])
            for row in actual_document_counts
        }
        expected_chunk_count = 0
        for row in document_rows:
            document_id = str(row[0])
            status = str(row[3])
            source_page_count = int(row[5])
            declared_counts = tuple(int(value) for value in row[6:9])
            if status == "indexed":
                if source_page_count != declared_counts[0]:
                    raise PageSearchIndexUnavailableError(
                        "page-search index counts are inconsistent"
                    )
                expected_counts = declared_counts
                expected_chunk_count += declared_counts[2]
            elif status in ("excluded", "pending"):
                if source_page_count != 0 or any(declared_counts):
                    raise PageSearchIndexUnavailableError(
                        "page-search index counts are inconsistent"
                    )
                expected_counts = (0, 0, 0)
            else:
                raise PageSearchIndexUnavailableError(
                    "page-search index status is invalid"
                )
            if actual_counts_by_id.get(document_id) != expected_counts:
                raise PageSearchIndexUnavailableError(
                    "page-search index counts are inconsistent"
                )
        if int(fts_count) != expected_chunk_count:
            raise PageSearchIndexUnavailableError(
                "page-search index counts are inconsistent"
            )
        if any(
            type(row[0]) is not str
            or not row[0].strip()
            or len(row[0]) > MAX_PRINTED_PAGE_CHARS
            or _contains_control(row[0])
            for row in printed_pages
        ) or any(
            type(row[0]) is not str
            or not row[0]
            or len(row[0]) > 1_024
            or _contains_control(row[0])
            for row in chunk_ids
        ):
            raise PageSearchIndexUnavailableError(
                "page-search index citations are unsafe"
            )


def build_page_search_index(
    *,
    database: Path,
    plan: PageSearchBuildPlan,
) -> PageSearchIndexStatus:
    """Atomically build an index from an owner-resolved immutable plan."""
    if type(plan) is not PageSearchBuildPlan:
        raise PageSearchBuildPlanError(
            "page-search build plan has an unsupported type"
        )
    try:
        fresh_plan = PageSearchBuildPlan(
            documents=plan._inputs,
            contract_version=plan.contract_version,
            slice_id=plan.slice_id,
        )
    except (TypeError, ValueError) as error:
        raise PageSearchBuildPlanError(
            "page-search build plan is stale or invalid"
        ) from error
    if fresh_plan != plan:
        raise PageSearchBuildPlanError(
            "page-search build plan is stale or invalid"
        )
    plan = fresh_plan
    database = Path(database)
    database.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    documents = tuple(
        _indexed_document(document)
        if document.status == "indexed"
        else _pending_document(document)
        for document in plan._documents
    )

    stage = _new_stage(database)
    try:
        _write_index(stage, plan, documents)
        PageSearchIndex(stage).status()
        _sync_file(stage)
        os.replace(stage, database)
        os.chmod(database, 0o600)
        _sync_directory(database.parent)
    except Exception:
        stage.unlink(missing_ok=True)
        stage.with_name(stage.name + "-journal").unlink(missing_ok=True)
        stage.with_name(stage.name + "-wal").unlink(missing_ok=True)
        raise
    return PageSearchIndex(database).status()


def _indexed_document(document: _ResolvedDocument) -> PageSearchDocument:
    chunks = tuple(_iter_chunks(document))
    searchable_pages = sum(
        _page_has_searchable_text(page) for page in document.pages
    )
    return PageSearchDocument(
        document.document_id,
        document.filename,
        document.title,
        "indexed",
        document.status_reason,
        document.source_page_count,
        document.source_paragraph_count,
        len(document.pages),
        searchable_pages,
        len(chunks),
    )


def _pending_document(document: _ResolvedDocument) -> PageSearchDocument:
    return PageSearchDocument(
        document.document_id,
        document.filename,
        document.title,
        "pending",
        document.status_reason,
        0,
        0,
        0,
        0,
        0,
    )


def _page_has_searchable_text(page: _ResolvedPage) -> bool:
    return any(_sanitize_evidence_text(unit) for unit in page.text_units)


def _iter_chunks(document: _ResolvedDocument) -> Sequence[_Chunk]:
    chunks: list[_Chunk] = []
    for page in document.pages:
        text = " ".join(
            safe
            for unit in page.text_units
            if (safe := _sanitize_evidence_text(unit))
        )
        for ordinal, chunk_text in enumerate(_split_page_text(text), start=1):
            chunks.append(
                _Chunk(
                    f"{document.document_id}-p{page.physical_page:04d}-c{ordinal:02d}",
                    document.document_id,
                    page.physical_page,
                    page.printed_page,
                    ordinal,
                    chunk_text,
                )
            )
    return chunks


def _split_page_text(text: str) -> tuple[str, ...]:
    remaining = text.strip()
    if not remaining:
        return ()
    chunks: list[str] = []
    while len(remaining) > MAX_CHUNK_CHARS:
        cut = remaining.rfind(" ", 0, MAX_CHUNK_CHARS + 1)
        if cut <= 0:
            cut = MAX_CHUNK_CHARS
        chunks.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        chunks.append(remaining)
    return tuple(chunks)


def _new_stage(database: Path) -> Path:
    descriptor, name = tempfile.mkstemp(
        prefix=f".{database.name}.",
        suffix=".tmp",
        dir=database.parent,
    )
    os.close(descriptor)
    stage = Path(name)
    os.chmod(stage, 0o600)
    return stage


def _write_index(
    stage: Path,
    plan: PageSearchBuildPlan,
    documents: Sequence[PageSearchDocument],
) -> None:
    connection = sqlite3.connect(stage)
    try:
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA temp_store = MEMORY")
        connection.executescript(_SCHEMA)
        connection.execute("BEGIN IMMEDIATE")
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            (
                ("schema_version", SCHEMA_VERSION),
                ("slice_id", plan.slice_id),
                ("build_plan_contract_version", plan.contract_version),
            ),
        )
        resolved_by_id = {
            document.document_id: document for document in plan._documents
        }
        connection.executemany(
            """
            INSERT INTO documents(
                document_id, filename, title, status, status_reason,
                projection_result_id, source_page_count,
                source_paragraph_count,
                indexed_page_count, searchable_page_count, chunk_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    document.document_id,
                    document.filename,
                    document.title,
                    document.status,
                    document.status_reason,
                    resolved_by_id[document.document_id].projection_result_id,
                    document.source_page_count,
                    document.source_paragraph_count,
                    document.indexed_page_count,
                    document.searchable_page_count,
                    document.chunk_count,
                )
                for document in documents
            ),
        )
        for resolved in plan._documents:
            if resolved.status != "indexed":
                continue
            connection.executemany(
                """
                INSERT INTO pages(
                    document_id, physical_page, printed_page, has_text
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    (
                        resolved.document_id,
                        page.physical_page,
                        page.printed_page,
                        _page_has_searchable_text(page),
                    )
                    for page in resolved.pages
                ),
            )
            connection.executemany(
                """
                INSERT INTO chunks(
                    chunk_id, document_id, physical_page, printed_page,
                    chunk_ordinal, text
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        chunk.chunk_id,
                        chunk.document_id,
                        chunk.physical_page,
                        chunk.printed_page,
                        chunk.chunk_ordinal,
                        chunk.text,
                    )
                    for chunk in _iter_chunks(resolved)
                ),
            )
        connection.execute(
            "INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')"
        )
        connection.execute(
            "INSERT INTO chunks_fts(chunks_fts, rank) "
            "VALUES('integrity-check', 1)"
        )
        connection.commit()
        connection.execute("VACUUM")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _metadata(connection: sqlite3.Connection) -> dict[str, str]:
    return dict(connection.execute("SELECT key, value FROM metadata"))


def _validate_schema_and_slice(metadata: dict[str, str]) -> None:
    schema_version = metadata["schema_version"]
    if schema_version not in (LEGACY_SCHEMA_VERSION, SCHEMA_VERSION):
        raise PageSearchIndexUnavailableError(
            "page-search index schema is unsupported"
        )
    if metadata["slice_id"] != SLICE_ID:
        raise PageSearchIndexUnavailableError("page-search index is invalid")
    if (
        schema_version == SCHEMA_VERSION
        and metadata.get("build_plan_contract_version")
        != BUILD_PLAN_CONTRACT_VERSION
    ):
        raise PageSearchIndexUnavailableError("page-search index is invalid")


def _validate_query(
    query: str,
    limit: int,
    offset: int,
) -> tuple[str, str]:
    if not isinstance(query, str):
        raise PageSearchQueryError("query must be text")
    if _contains_control(query):
        raise PageSearchQueryError(
            "query must not contain control or formatting characters"
        )
    normalized = " ".join(query.split())
    if not normalized or len(normalized) > MAX_QUERY_CHARS:
        raise PageSearchQueryError(
            f"query must contain 1 to {MAX_QUERY_CHARS} characters"
        )
    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or not 1 <= limit <= MAX_LIMIT
    ):
        raise PageSearchQueryError(f"limit must be between 1 and {MAX_LIMIT}")
    if (
        not isinstance(offset, int)
        or isinstance(offset, bool)
        or not 0 <= offset <= MAX_OFFSET
    ):
        raise PageSearchQueryError(f"offset must be between 0 and {MAX_OFFSET}")
    terms = _QUERY_TERM.findall(normalized)
    if not terms or len(terms) > MAX_QUERY_TERMS:
        raise PageSearchQueryError(
            f"query must contain 1 to {MAX_QUERY_TERMS} searchable terms"
        )
    match_expression = " AND ".join(
        f'"{term.replace(chr(34), chr(34) * 2)}"' for term in terms
    )
    return normalized, match_expression


def _contains_control(value: str) -> bool:
    return any(
        unicodedata.category(character).startswith("C") for character in value
    )


def _sanitize_evidence_text(value: str) -> str:
    without_controls = "".join(
        " " if unicodedata.category(character).startswith("C") else character
        for character in value
    )
    return " ".join(without_controls.split())


def _bounded_snippet(value: str) -> str:
    normalized = _sanitize_evidence_text(value)
    if len(normalized) <= MAX_SNIPPET_CHARS:
        return normalized
    return normalized[: MAX_SNIPPET_CHARS - 1].rstrip() + "…"


def _document_from_row(row: Sequence[Any]) -> PageSearchDocument:
    return PageSearchDocument(
        document_id=str(row[0]),
        filename=str(row[1]),
        title=str(row[2]),
        status=cast(_DOCUMENT_STATUS, row[3]),
        status_reason=str(row[4]),
        source_page_count=int(row[5]),
        source_paragraph_count=int(row[6]),
        indexed_page_count=int(row[7]),
        searchable_page_count=int(row[8]),
        chunk_count=int(row[9]),
    )


def _sync_file(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

"""Retrieval tests for bounded deterministic MongoDB BM25 search."""

from __future__ import annotations

from dataclasses import replace
from typing import cast

import mongomock
import pytest
from projectkoios.indexing.mongodb_page_projection_lexical import (
    MongoPageProjectionLexicalError,
    MongoPageProjectionLexicalProjector,
    MongoPageProjectionLexicalRetriever,
)
from projectkoios.search.page_projection_chunking import PageProjectionChunk
from projectkoios.search.page_projection_lexical import (
    PageProjectionLexicalSearchRequest,
)
from pymongo.database import Database

from tests.projectkoios.search.page_projection_chunking.fixture.chunking import (  # noqa: E501
    derive_chunking_result,
)

MongoDocument = dict[str, object]


def _database() -> Database[MongoDocument]:
    """Return one isolated in-memory Mongo-compatible database."""

    return cast(Database[MongoDocument], mongomock.MongoClient()["retrieval"])


def _active_retriever() -> tuple[
    MongoPageProjectionLexicalRetriever,
    tuple[PageProjectionChunk, ...],
]:
    """Stage and activate the exact two-chunk producer fixture.

    Returns
    -------
    tuple
        Retriever and exact structurally typed Search chunks.
    """

    database = _database()
    chunks = tuple(derive_chunking_result().chunks)
    projector = MongoPageProjectionLexicalProjector(
        database=database,
        storage_target_id="projectkoios.search.mongodb.development",
    )
    generation = projector.stage(chunks=chunks)
    projector.activate(
        generation=generation,
        expected_active_generation_id=None,
    )
    return (
        MongoPageProjectionLexicalRetriever(
            database=database,
            storage_target_id="projectkoios.search.mongodb.development",
        ),
        chunks,
    )


def test__search__returns_bounded_bm25_hits_with_generation_identity() -> None:
    """Return exact matching chunk identities and immutable index provenance."""

    retriever, chunks = _active_retriever()

    result = retriever.search(
        request=PageProjectionLexicalSearchRequest(query="canonical")
    )

    assert len(result.hits) == 1
    assert result.hits[0].chunk_id == chunks[0].chunk_id
    assert result.hits[0].matched_terms == ("canonical",)
    assert result.hits[0].rank == 1
    assert result.hits[0].score > 0.0
    assert result.generation_id.startswith(
        "page-projection-lexical-generation:sha256:"
    )
    assert result.index_id.startswith("page-projection-lexical-index:sha256:")
    assert result.result_id.startswith(
        "page-projection-lexical-search-result:sha256:"
    )


def test__search__orders_equal_scores_by_chunk_identity() -> None:
    """Break equal BM25 scores by ascending stable chunk identity."""

    retriever, chunks = _active_retriever()

    result = retriever.search(
        request=PageProjectionLexicalSearchRequest(
            query="canonical figure",
            limit=2,
        )
    )

    assert tuple(hit.chunk_id for hit in result.hits) == tuple(
        sorted(chunk.chunk_id for chunk in chunks)
    )
    assert result.hits[0].score == result.hits[1].score
    assert tuple(hit.rank for hit in result.hits) == (1, 2)


def test__search__fails_closed_at_candidate_posting_bound() -> None:
    """Stop rather than truncate an over-bound posting candidate set."""

    retriever, _ = _active_retriever()

    with pytest.raises(MongoPageProjectionLexicalError, match="posting bound"):
        retriever.search(
            request=PageProjectionLexicalSearchRequest(
                query="canonical figure",
                maximum_candidate_postings=1,
            )
        )


def test__stage__counts_repeated_term_once_for_document_frequency() -> None:
    """Keep posting term frequency while counting one document occurrence."""

    database = _database()
    chunks = tuple(derive_chunking_result().chunks)
    repeated = replace(chunks[0], text="repeat repeat other")
    projector = MongoPageProjectionLexicalProjector(
        database=database,
        storage_target_id="projectkoios.search.mongodb.development",
    )
    generation = projector.stage(chunks=(repeated, chunks[1]))
    term_statistic = database[projector.STATISTICS_COLLECTION].find_one(
        {
            "generation_id": generation.generation_id,
            "document_type": "term-statistic",
            "term": "repeat",
        }
    )
    posting = database[projector.POSTINGS_COLLECTION].find_one(
        {
            "generation_id": generation.generation_id,
            "term": "repeat",
        }
    )
    assert term_statistic is not None
    assert term_statistic["document_frequency"] == 1
    assert posting is not None
    assert posting["term_frequency"] == 2
    projector.activate(
        generation=generation,
        expected_active_generation_id=None,
    )
    retriever = MongoPageProjectionLexicalRetriever(
        database=database,
        storage_target_id="projectkoios.search.mongodb.development",
    )
    request = PageProjectionLexicalSearchRequest(query="repeat")

    first = retriever.search(request=request)
    second = retriever.search(request=request)

    assert second == first
    assert tuple(hit.chunk_id for hit in first.hits) == (repeated.chunk_id,)
    assert tuple(hit.rank for hit in first.hits) == (1,)
    assert first.hits[0].score.hex() == "0x1.cdfd1e9763637p-1"


def test__search__returns_exact_empty_hits_for_absent_normalized_term() -> None:
    """Retain active provenance when a valid normalized term has no posting."""

    retriever, _ = _active_retriever()
    active = retriever.active_generation()
    assert active is not None

    result = retriever.search(
        request=PageProjectionLexicalSearchRequest(query="absentterm")
    )

    assert result.normalized_query_terms == ("absentterm",)
    assert result.hits == ()
    assert result.generation == active
    assert result.generation_id == active.generation_id
    assert result.corpus_id == active.corpus_id
    assert result.index_id == active.index_id


def test__search__requires_one_verified_active_generation() -> None:
    """Reject retrieval when no generation has passed atomic activation."""

    database = _database()
    retriever = MongoPageProjectionLexicalRetriever(
        database=database,
        storage_target_id="projectkoios.search.mongodb.development",
    )

    with pytest.raises(
        MongoPageProjectionLexicalError, match="active generation"
    ):
        retriever.search(
            request=PageProjectionLexicalSearchRequest(query="canonical")
        )

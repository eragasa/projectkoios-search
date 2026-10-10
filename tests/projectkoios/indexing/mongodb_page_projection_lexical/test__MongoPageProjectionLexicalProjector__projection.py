"""Projection tests for immutable MongoDB lexical generations."""

from __future__ import annotations

from dataclasses import replace
from typing import cast

import mongomock
import pytest
from mongomock.collection import Collection as MongoMockCollection
from projectkoios.indexing.mongodb_page_projection_lexical import (
    MongoPageProjectionLexicalError,
    MongoPageProjectionLexicalProjector,
)
from projectkoios.search.page_projection_lexical import (
    PageProjectionLexicalChunk,
)
from pymongo import IndexModel
from pymongo.database import Database

from tests.projectkoios.search.page_projection_chunking.fixture.chunking import (  # noqa: E501
    derive_chunking_result,
)

MongoDocument = dict[str, object]


def _database(name: str) -> Database[MongoDocument]:
    """Return one isolated in-memory Mongo-compatible database.

    Parameters
    ----------
    name
        Database name used only within the in-memory client.

    Returns
    -------
    pymongo.database.Database
        Injected database capability with no network or credentials.
    """

    client = mongomock.MongoClient()
    return cast(Database[MongoDocument], client[name])


def _chunks() -> tuple[PageProjectionLexicalChunk, ...]:
    """Return exact Search ``PageProjectionChunk`` outputs structurally.

    Returns
    -------
    tuple[PageProjectionLexicalChunk, ...]
        Paragraph and figure-caption chunks from the frozen producer fixture.
    """

    values = tuple(derive_chunking_result().chunks)
    assert all(
        isinstance(value, PageProjectionLexicalChunk) for value in values
    )
    return cast(tuple[PageProjectionLexicalChunk, ...], values)


def _generation_documents(
    database: Database[MongoDocument],
) -> dict[str, tuple[MongoDocument, ...]]:
    """Return canonical generation-scoped documents from every collection.

    Parameters
    ----------
    database
        Database whose documents are observed.

    Returns
    -------
    dict[str, tuple[MongoDocument, ...]]
        Documents ordered by deterministic Mongo ``_id``.
    """

    names = (
        MongoPageProjectionLexicalProjector.CHUNKS_COLLECTION,
        MongoPageProjectionLexicalProjector.POSTINGS_COLLECTION,
        MongoPageProjectionLexicalProjector.STATISTICS_COLLECTION,
        MongoPageProjectionLexicalProjector.GENERATIONS_COLLECTION,
    )
    return {
        name: tuple(database[name].find({}, sort=[("_id", 1)]))
        for name in names
    }


def test__ensure_indexes__uses_strict_pymongo_list_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass lists and both exact unique definitions to the driver boundary."""

    observed: list[tuple[str, bool, tuple[tuple[str, object], ...]]] = []
    original = MongoMockCollection.create_indexes

    def strict_create_indexes(
        self: MongoMockCollection,
        indexes: list[IndexModel],
        session: object | None = None,
    ) -> list[str]:
        if type(indexes) is not list:
            raise TypeError("indexes must be a list")
        observed.extend(
            (
                cast(str, index.document["name"]),
                index.document.get("unique") is True,
                tuple(index.document["key"].items()),
            )
            for index in indexes
        )
        return original(self, indexes, session=session)

    monkeypatch.setattr(
        MongoMockCollection,
        "create_indexes",
        strict_create_indexes,
    )
    projector = MongoPageProjectionLexicalProjector(
        database=_database("strict-index-contract"),
        storage_target_id="projectkoios.search.mongodb.development",
    )

    projector.ensure_indexes()

    assert observed == [
        (
            "generation_chunk_unique",
            True,
            (("generation_id", 1), ("chunk_id", 1)),
        ),
        (
            "generation_term_chunk_unique",
            True,
            (("generation_id", 1), ("term", 1), ("chunk_id", 1)),
        ),
    ]


def test__stage__builds_verified_immutable_generation_idempotently() -> None:
    """Write all four schemas and verify exact deterministic measures."""

    database = _database("stage")
    projector = MongoPageProjectionLexicalProjector(
        database=database,
        storage_target_id="projectkoios.search.mongodb.development",
    )
    chunks = _chunks()

    first = projector.stage(chunks=chunks)
    second = projector.stage(chunks=tuple(reversed(chunks)))

    assert second == first
    assert first.chunk_count == 2
    assert first.posting_count == 4
    assert first.term_count == 4
    assert first.total_document_length == 4
    assert database[projector.CHUNKS_COLLECTION].count_documents({}) == 2
    assert database[projector.POSTINGS_COLLECTION].count_documents({}) == 4
    assert database[projector.STATISTICS_COLLECTION].count_documents({}) == 5
    metadata = database[projector.GENERATIONS_COLLECTION].find_one(
        {"_id": first.generation_id}
    )
    assert metadata is not None
    assert metadata["status"] == "ready"
    assert projector.active_generation() is None

    chunk_indexes = database[projector.CHUNKS_COLLECTION].index_information()
    posting_indexes = database[
        projector.POSTINGS_COLLECTION
    ].index_information()
    assert "generation_chunk_unique" in chunk_indexes
    assert "generation_term_chunk_unique" in posting_indexes


def test__stage__is_clean_rebuild_equivalent_across_databases() -> None:
    """Produce identical identities and documents independent of input order."""

    first_database = _database("first")
    second_database = _database("second")
    first = MongoPageProjectionLexicalProjector(
        database=first_database,
        storage_target_id="projectkoios.search.mongodb.development",
    )
    second = MongoPageProjectionLexicalProjector(
        database=second_database,
        storage_target_id="projectkoios.search.mongodb.development",
    )
    chunks = _chunks()

    first_generation = first.stage(chunks=chunks)
    second_generation = second.stage(chunks=tuple(reversed(chunks)))

    assert second_generation == first_generation
    assert _generation_documents(second_database) == _generation_documents(
        first_database
    )


def test__activate__uses_single_pointer_compare_and_set() -> None:
    """Switch active generations atomically and reject stale expectations."""

    database = _database("activation")
    projector = MongoPageProjectionLexicalProjector(
        database=database,
        storage_target_id="projectkoios.search.mongodb.development",
    )
    chunks = _chunks()
    first = projector.stage(chunks=chunks)
    assert (
        projector.activate(
            generation=first,
            expected_active_generation_id=None,
        )
        == first
    )

    changed_chunks = (
        replace(chunks[0], text="Changed canonical paragraph."),
        chunks[1],
    )
    second = projector.stage(chunks=changed_chunks)

    with pytest.raises(
        MongoPageProjectionLexicalError, match="compare-and-set"
    ):
        projector.activate(
            generation=second,
            expected_active_generation_id="stale-generation",
        )
    assert projector.active_generation() == first

    assert (
        projector.activate(
            generation=second,
            expected_active_generation_id=first.generation_id,
        )
        == second
    )
    assert projector.active_generation() == second


def test__stage__rejects_duplicate_or_nonstructural_chunks() -> None:
    """Fail before readiness when the structural corpus is not exact."""

    database = _database("invalid")
    projector = MongoPageProjectionLexicalProjector(
        database=database,
        storage_target_id="projectkoios.search.mongodb.development",
    )
    chunks = _chunks()

    with pytest.raises(MongoPageProjectionLexicalError, match="validation"):
        projector.stage(chunks=(chunks[0], chunks[0]))
    with pytest.raises(
        MongoPageProjectionLexicalError,
        match="PageProjectionLexicalChunk",
    ):
        projector.stage(
            chunks=cast(tuple[PageProjectionLexicalChunk, ...], (object(),))
        )


def test__activate__reverifies_staged_documents_fail_closed() -> None:
    """Refuse activation after any generation-scoped document is altered."""

    database = _database("tamper")
    projector = MongoPageProjectionLexicalProjector(
        database=database,
        storage_target_id="projectkoios.search.mongodb.development",
    )
    generation = projector.stage(chunks=_chunks())
    database[projector.CHUNKS_COLLECTION].update_one(
        {"generation_id": generation.generation_id},
        {"$set": {"text": "tampered"}},
    )

    with pytest.raises(MongoPageProjectionLexicalError, match="verification"):
        projector.activate(
            generation=generation,
            expected_active_generation_id=None,
        )


def test__activate__rejects_generation_metadata_drift() -> None:
    """Require exact metadata keys and bindings before pointer activation."""

    database = _database("metadata-tamper")
    projector = MongoPageProjectionLexicalProjector(
        database=database,
        storage_target_id="projectkoios.search.mongodb.development",
    )
    generation = projector.stage(chunks=_chunks())
    database[projector.GENERATIONS_COLLECTION].update_one(
        {"_id": generation.generation_id},
        {"$set": {"unexpected": "drift"}},
    )

    with pytest.raises(MongoPageProjectionLexicalError, match="metadata"):
        projector.activate(
            generation=generation,
            expected_active_generation_id=None,
        )

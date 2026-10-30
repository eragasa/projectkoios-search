"""Focused tests for bounded current-schema corpus-union admission."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import cast

import mongomock
import pytest
from projectkoios.indexing.mongodb_page_projection_lexical import (
    MongoPageProjectionLexicalProjector,
)
from projectkoios.search.page_projection_lexical import (
    PageProjectionLexicalIdentity,
)
from pymongo.database import Database

from scripts import page_projection_lexical_admission as admission
from tests.projectkoios.search.page_projection_chunking.fixture.chunking import (  # noqa: E501
    derive_chunking_result,
)

MongoDocument = dict[str, object]


def _database(name: str) -> Database[MongoDocument]:
    client: mongomock.MongoClient[MongoDocument] = mongomock.MongoClient()
    return cast(Database[MongoDocument], client[name])


def _arguments() -> admission.AdmissionArguments:
    return admission.AdmissionArguments(
        publication_root=Path("/private/publications"),
        source_sha256="a" * 64,
        source_byte_length=13_776_899,
        source_media_type="application/pdf",
        source_artifact_id="managed-artifact:sha256:" + "b" * 64,
        pipeline_configuration_id=(
            "page-projection-publication-pipeline:sha256:" + "c" * 64
        ),
        publication_id="page-projection-publication:sha256:" + "d" * 64,
        receipt_id=("page-projection-publication-receipt:sha256:" + "e" * 64),
        receipt_sha256="e" * 64,
        receipt_byte_length=2_955,
        payload_id="page-projection-publication-payload:sha256:" + "f" * 64,
        payload_sha256="1" * 64,
        payload_byte_length=116_343_576,
        page_projection_result_id=("page-projection-result:sha256:" + "2" * 64),
        enrichment_result_id=(
            "page-projection-evidence-enrichment-result:sha256:" + "3" * 64
        ),
        maximum_payload_bytes=116_343_576,
        expected_load_request_id=(
            "page-projection-publication-load-request:sha256:" + "4" * 64
        ),
        expected_load_result_id=(
            "page-projection-publication-load-result:sha256:" + "5" * 64
        ),
        expected_page_count=780,
        expected_chunk_count=16_985,
        expected_enrichment_available_count=16_985,
        expected_enrichment_unavailable_count=0,
        expected_paragraph_count=16_985,
        expected_heading_count=0,
        expected_figure_caption_count=0,
        expected_chunking_request_id=(
            "page-projection-chunking-request:sha256:" + "6" * 64
        ),
        expected_chunk_inventory_id=(
            "page-projection-chunk-inventory:sha256:" + "7" * 64
        ),
        expected_chunking_result_id=(
            "page-projection-chunking-result:sha256:" + "8" * 64
        ),
        expected_document_chunk_manifest_sha256="9" * 64,
        smoke_query="matrix computations golub van loan",
        smoke_limit=5,
    )


def _loaded_target() -> admission.LoadedDocument:
    chunks = tuple(derive_chunking_result().chunks)
    target = replace(
        chunks[1],
        page_projection_result_id=("page-projection-result:sha256:" + "a" * 64),
    )
    return admission.LoadedDocument(
        load_request_id="load-request",
        load_result_id="load-result",
        chunking_request_id="chunking-request",
        chunk_inventory_id="chunk-inventory",
        chunking_result_id="chunking-result",
        page_count=1,
        enrichment_available_count=1,
        enrichment_unavailable_count=0,
        chunks=(target,),
        style_counts={target.style.value: 1},
        chunk_manifest_sha256=(
            PageProjectionLexicalIdentity.chunk_manifest_sha256(
                chunk_ids=(target.chunk_id,)
            )
        ),
    )


@contextmanager
def _connection_fd(value: bytes) -> Iterator[None]:
    try:
        saved = os.dup(3)
    except OSError:
        saved = None
    reader, writer = os.pipe()
    try:
        os.write(writer, value)
    finally:
        os.close(writer)
    if reader != 3:
        os.dup2(reader, 3)
        os.close(reader)
    try:
        yield
    finally:
        try:
            os.close(3)
        except OSError:
            pass
        if saved is not None:
            os.dup2(saved, 3)
            os.close(saved)


def test__union_plan__preserves_every_active_chunk_and_adds_target() -> None:
    database = _database("union-preservation")
    projector = MongoPageProjectionLexicalProjector(
        database=database,
        storage_target_id=admission.STORAGE_TARGET_ID,
    )
    existing = tuple(derive_chunking_result().chunks)[:1]
    first = projector.stage(chunks=existing)
    projector.activate(
        generation=first,
        expected_active_generation_id=None,
        expected_active_pointer_revision=None,
    )
    before = projector.active_snapshot()

    plan = admission.union_plan(
        projector=projector,
        snapshot=before,
        document=_loaded_target(),
    )

    assert plan.active_chunks == existing
    assert plan.added_chunk_count == 1
    assert plan.overlapping_chunk_count == 0
    assert {value.chunk_id for value in plan.union_chunks} == {
        existing[0].chunk_id,
        _loaded_target().chunks[0].chunk_id,
    }
    staged = projector.stage(chunks=plan.union_chunks)
    projector.activate(
        generation=staged,
        expected_active_generation_id=before.generation_id,
        expected_active_pointer_revision=before.pointer_revision,
    )
    after = projector.active_snapshot()
    assert after.generation == plan.generation
    assert after.pointer_revision == 2


def test__union_stage_replay_is_idempotent_without_pointer_change() -> None:
    database = _database("union-replay")
    projector = MongoPageProjectionLexicalProjector(
        database=database,
        storage_target_id=admission.STORAGE_TARGET_ID,
    )
    document = _loaded_target()
    empty = projector.active_snapshot()
    plan = admission.union_plan(
        projector=projector,
        snapshot=empty,
        document=document,
    )
    first = projector.stage(chunks=plan.union_chunks)
    projector.activate(
        generation=first,
        expected_active_generation_id=None,
        expected_active_pointer_revision=None,
    )
    pointer_before = database[projector.GENERATIONS_COLLECTION].find_one(
        {"_id": "active"}
    )

    replay = projector.stage(chunks=tuple(reversed(plan.union_chunks)))

    assert replay == first
    assert (
        database[projector.GENERATIONS_COLLECTION].find_one({"_id": "active"})
        == pointer_before
    )
    assert (
        database[projector.CHUNKS_COLLECTION].count_documents(
            {"generation_id": first.generation_id}
        )
        == 1
    )


def test__run_admission__cas_mismatch_performs_no_stage_or_pointer_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client: mongomock.MongoClient[MongoDocument] = mongomock.MongoClient()
    database = cast(Database[MongoDocument], client[admission.DATABASE_NAME])
    projector = MongoPageProjectionLexicalProjector(
        database=database,
        storage_target_id=admission.STORAGE_TARGET_ID,
    )
    existing = tuple(derive_chunking_result().chunks)[:1]
    generation = projector.stage(chunks=existing)
    projector.activate(
        generation=generation,
        expected_active_generation_id=None,
        expected_active_pointer_revision=None,
    )
    before_documents = {
        name: tuple(database[name].find({}, sort=[("_id", 1)]))
        for name in (
            projector.CHUNKS_COLLECTION,
            projector.POSTINGS_COLLECTION,
            projector.STATISTICS_COLLECTION,
            projector.GENERATIONS_COLLECTION,
        )
    }
    monkeypatch.setattr(
        admission,
        "load_document",
        lambda *, arguments: _loaded_target(),
    )
    monkeypatch.setattr(
        admission,
        "create_client",
        lambda *, connection_uri: client,
    )
    arguments = replace(
        _arguments(),
        expected_active_generation_id="page-projection-lexical-generation:sha256:"
        + "f" * 64,
        expected_active_pointer_revision=1,
        expected_union_generation_id="page-projection-lexical-generation:sha256:"
        + "e" * 64,
        expected_union_chunk_manifest_sha256="d" * 64,
        expected_union_chunk_count=2,
    )

    with pytest.raises(admission.AdmissionCASError):
        admission.run_admission(
            arguments=arguments,
            connection_uri="secret-connection-material",
        )

    after_documents = {
        name: tuple(database[name].find({}, sort=[("_id", 1)]))
        for name in before_documents
    }
    assert after_documents == before_documents


def test__run_admission__activates_then_replays_without_pointer_increment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client: mongomock.MongoClient[MongoDocument] = mongomock.MongoClient()
    database = cast(Database[MongoDocument], client[admission.DATABASE_NAME])
    projector = MongoPageProjectionLexicalProjector(
        database=database,
        storage_target_id=admission.STORAGE_TARGET_ID,
    )
    document = _loaded_target()
    projector.ensure_indexes()
    plan = admission.union_plan(
        projector=projector,
        snapshot=projector.active_snapshot(),
        document=document,
    )
    monkeypatch.setattr(
        admission,
        "load_document",
        lambda *, arguments: document,
    )
    monkeypatch.setattr(
        admission,
        "create_client",
        lambda *, connection_uri: client,
    )
    first_arguments = replace(
        _arguments(),
        page_projection_result_id=(
            document.chunks[0].page_projection_result_id
        ),
        smoke_query="figure",
        expected_union_generation_id=plan.generation.generation_id,
        expected_union_chunk_manifest_sha256=(
            plan.generation.chunk_manifest_sha256
        ),
        expected_union_chunk_count=1,
    )

    first = admission.run_admission(
        arguments=first_arguments,
        connection_uri="secret-connection-material",
    )
    pointer_after_first = database[projector.GENERATIONS_COLLECTION].find_one(
        {"_id": "active"}
    )
    assert first["disposition"] == "activated"
    assert first["pointer_changed"] is True
    assert first["retrieval_result_id"] == first["retrieval_replay_result_id"]
    assert len(cast(list[dict[str, object]], first["hit_locators"])) == 1

    replay_arguments = replace(
        first_arguments,
        expected_active_generation_id=plan.generation.generation_id,
        expected_active_pointer_revision=1,
    )
    replay = admission.run_admission(
        arguments=replay_arguments,
        connection_uri="secret-connection-material",
    )

    assert replay["disposition"] == "replayed-identical"
    assert replay["pointer_changed"] is False
    assert (
        database[projector.GENERATIONS_COLLECTION].find_one({"_id": "active"})
        == pointer_after_first
    )


def test__exact_golub_inventory_gate_accepts_only_all_pinned_counts() -> None:
    arguments = _arguments()

    admission.validate_document_inventory(
        arguments=arguments,
        page_count=780,
        block_count=16_985,
        enrichment_available_count=16_985,
        enrichment_unavailable_count=0,
        chunk_count=16_985,
        style_counts={"paragraph": 16_985},
        chunking_request_id=arguments.expected_chunking_request_id,
        chunk_inventory_id=arguments.expected_chunk_inventory_id,
        chunking_result_id=arguments.expected_chunking_result_id,
        chunk_manifest_sha256=(
            arguments.expected_document_chunk_manifest_sha256
        ),
    )

    with pytest.raises(admission.AdmissionInventoryError):
        admission.validate_document_inventory(
            arguments=arguments,
            page_count=780,
            block_count=16_984,
            enrichment_available_count=16_985,
            enrichment_unavailable_count=0,
            chunk_count=16_985,
            style_counts={"paragraph": 16_985},
            chunking_request_id=arguments.expected_chunking_request_id,
            chunk_inventory_id=arguments.expected_chunk_inventory_id,
            chunking_result_id=arguments.expected_chunking_result_id,
            chunk_manifest_sha256=(
                arguments.expected_document_chunk_manifest_sha256
            ),
        )


@pytest.mark.parametrize(
    "secret",
    (
        b"",
        b" leading",
        b"trailing ",
        b"line\nbreak",
        b"control\x00value",
        b"x" * 8_193,
    ),
)
def test__credential_channel__rejects_unsafe_values_and_closes_fd3(
    secret: bytes,
) -> None:
    with _connection_fd(secret):
        with pytest.raises(admission.AdmissionInvocationError):
            admission.read_connection_uri()
        with pytest.raises(OSError):
            os.fstat(3)


def test__credential_channel__returns_secret_without_output(
    capfd: pytest.CaptureFixture[str],
) -> None:
    with _connection_fd(b"secret-connection-material"):
        value = admission.read_connection_uri()
    captured = capfd.readouterr()

    assert value == "secret-connection-material"
    assert captured.out == ""
    assert captured.err == ""


def test__output_validation__rejects_extra_fields_and_never_emits_secret(
    capfd: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(admission.AdmissionOutputError):
        admission.emit_record(
            record={
                "category": "connection",
                "exit_code": 5,
                "phase": "admission",
                "status": "failed",
                "secret": "secret-connection-material",
            },
            expected_keys=admission._FAILURE_KEYS,
        )
    captured = capfd.readouterr()

    assert captured.out == ""
    assert captured.err == ""

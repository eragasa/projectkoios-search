from __future__ import annotations

from pathlib import Path

import pytest
from projectkoios.chunking import TextChunk
from projectkoios.indexing import InMemoryRoleScopedChunkIndex
from projectkoios.search import (
    CorpusRole,
    RoleScopedChunk,
    RoleScopedSearchRequest,
    RoleScopedSearchService,
)


def chunk(text: str, index: int) -> TextChunk:
    return TextChunk(
        source_path=Path(f"source/{index}.txt"),
        source_kind="textbook",
        language="text",
        chunk_index=index,
        start_line=1,
        end_line=1,
        text=text,
    )


def record(
    record_id: str,
    text: str,
    role: CorpusRole,
    index: int,
) -> RoleScopedChunk:
    return RoleScopedChunk(record_id, chunk(text, index), role)


def request(
    *roles: CorpusRole,
    excluded: tuple[str, ...] = (),
) -> RoleScopedSearchRequest:
    return RoleScopedSearchRequest(
        query="entropy reversible path",
        allowed_roles=roles,
        excluded_record_ids=excluded,
        limit=10,
    )


def populated_index() -> InMemoryRoleScopedChunkIndex:
    index = InMemoryRoleScopedChunkIndex()
    index.add_records(
        (
            record(
                "evidence:1",
                "entropy is evaluated along a reversible path",
                CorpusRole.EVIDENCE,
                1,
            ),
            record(
                "problem:1",
                "entropy reversible path problem statement",
                CorpusRole.PROBLEM_MATERIAL,
                2,
            ),
            record(
                "generated:1",
                "entropy reversible path proposed solution",
                CorpusRole.GENERATED_SOLUTION,
                3,
            ),
            record(
                "reviewed:1",
                "entropy reversible path reviewed solution",
                CorpusRole.REVIEWED_SOLUTION,
                4,
            ),
        )
    )
    return index


def test__search__evidence_filter_prevents_solution_contamination() -> None:
    index = populated_index()

    results = index.search(request(CorpusRole.EVIDENCE))

    assert [result.record.record_id for result in results] == ["evidence:1"]
    assert all(
        result.record.corpus_role is CorpusRole.EVIDENCE for result in results
    )


def test__search__problem_material_requires_explicit_role() -> None:
    index = populated_index()

    results = index.search(request(CorpusRole.PROBLEM_MATERIAL))

    assert [result.record.record_id for result in results] == ["problem:1"]


def test__search__supports_multiple_explicit_roles_without_promotion() -> None:
    index = populated_index()

    results = index.search(
        request(CorpusRole.EVIDENCE, CorpusRole.REVIEWED_SOLUTION)
    )

    assert {result.record.corpus_role for result in results} == {
        CorpusRole.EVIDENCE,
        CorpusRole.REVIEWED_SOLUTION,
    }


def test__search__honors_excluded_record_identities() -> None:
    index = populated_index()

    results = index.search(
        request(CorpusRole.EVIDENCE, excluded=("evidence:1",))
    )

    assert results == ()


def test__search__uses_record_identity_as_deterministic_tie_break() -> None:
    index = InMemoryRoleScopedChunkIndex()
    index.add_records(
        (
            record("evidence:b", "entropy path", CorpusRole.EVIDENCE, 1),
            record("evidence:a", "entropy path", CorpusRole.EVIDENCE, 2),
        )
    )

    results = index.search(request(CorpusRole.EVIDENCE))

    assert [result.record.record_id for result in results] == [
        "evidence:a",
        "evidence:b",
    ]
    assert [result.rank for result in results] == [1, 2]


def test__add_records__rejects_identity_collision() -> None:
    index = InMemoryRoleScopedChunkIndex()
    item = record("evidence:1", "entropy", CorpusRole.EVIDENCE, 1)
    index.add_records((item,))

    with pytest.raises(ValueError, match="already exists"):
        index.add_records((item,))


def test__request__requires_an_explicit_corpus_role() -> None:
    with pytest.raises(ValueError, match="corpus role"):
        request()


def test__service__preserves_role_scoped_request() -> None:
    service = RoleScopedSearchService(populated_index())

    results = service.search(request(CorpusRole.EVIDENCE))

    assert len(results) == 1
    assert results[0].record.record_id == "evidence:1"

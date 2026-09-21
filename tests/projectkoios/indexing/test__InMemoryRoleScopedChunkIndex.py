from __future__ import annotations

from pathlib import Path

import pytest
from projectkoios.chunking import TextChunk
from projectkoios.indexing import InMemoryRoleScopedChunkIndex
from projectkoios.search import (
    CorpusRole,
    RetrievalPurpose,
    RoleScopedChunk,
    RoleScopedSearchRequest,
    RoleScopedSearchService,
    UnsupportedRetrievalPurposeError,
    course_material_admission_policy,
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
    admitted_purposes: tuple[RetrievalPurpose, ...],
) -> RoleScopedChunk:
    return RoleScopedChunk(
        record_id,
        chunk(text, index),
        role,
        admitted_purposes,
    )


def request(
    purpose: RetrievalPurpose,
    *,
    excluded: tuple[str, ...] = (),
) -> RoleScopedSearchRequest:
    return RoleScopedSearchRequest(
        query="entropy reversible path",
        purpose=purpose,
        excluded_record_ids=excluded,
        limit=10,
    )


def populated_index() -> InMemoryRoleScopedChunkIndex:
    index = InMemoryRoleScopedChunkIndex(
        admission_policy=course_material_admission_policy()
    )
    index.add_records(
        (
            record(
                "theory:1",
                "entropy is evaluated along a reversible path",
                CorpusRole.THEORY_EVIDENCE,
                1,
                (
                    RetrievalPurpose.PROBLEM_SOLVING,
                    RetrievalPurpose.LECTURE_AUTHORING,
                    RetrievalPurpose.CITATION_EVIDENCE,
                    RetrievalPurpose.ORDINARY_RAG,
                ),
            ),
            record(
                "source-example:1",
                "entropy reversible path worked example",
                CorpusRole.SOURCE_WORKED_EXAMPLE,
                2,
                (RetrievalPurpose.LECTURE_AUTHORING,),
            ),
            record(
                "source-solution:1",
                "entropy reversible path source solution",
                CorpusRole.SOURCE_SOLUTION,
                3,
                (RetrievalPurpose.LECTURE_AUTHORING,),
            ),
            record(
                "problem:1",
                "entropy reversible path problem statement",
                CorpusRole.PROBLEM_MATERIAL,
                4,
                (),
            ),
            record(
                "generated:1",
                "entropy reversible path proposed solution",
                CorpusRole.GENERATED_SOLUTION,
                5,
                (),
            ),
            record(
                "reviewed:1",
                "entropy reversible path reviewed solution",
                CorpusRole.REVIEWED_SOLUTION,
                6,
                (RetrievalPurpose.LECTURE_AUTHORING,),
            ),
        )
    )
    return index


def test__search__problem_solving_admits_only_theory_evidence() -> None:
    results = populated_index().search(
        request(RetrievalPurpose.PROBLEM_SOLVING)
    )

    assert [result.record.record_id for result in results] == ["theory:1"]
    assert all(
        result.record.corpus_role is CorpusRole.THEORY_EVIDENCE
        for result in results
    )


def test__search__lecture_authoring_admits_reviewed_material() -> None:
    results = populated_index().search(
        request(RetrievalPurpose.LECTURE_AUTHORING)
    )

    assert {result.record.corpus_role for result in results} == {
        CorpusRole.THEORY_EVIDENCE,
        CorpusRole.SOURCE_WORKED_EXAMPLE,
        CorpusRole.REVIEWED_SOLUTION,
    }


def test__search__lecture_authoring_excludes_unreviewed_solutions() -> None:
    results = populated_index().search(
        request(RetrievalPurpose.LECTURE_AUTHORING)
    )

    assert CorpusRole.GENERATED_SOLUTION not in {
        result.record.corpus_role for result in results
    }
    assert CorpusRole.SOURCE_SOLUTION not in {
        result.record.corpus_role for result in results
    }


@pytest.mark.parametrize(
    "purpose",
    (
        RetrievalPurpose.CITATION_EVIDENCE,
        RetrievalPurpose.ORDINARY_RAG,
    ),
)
def test__search__general_evidence_purposes_exclude_course_answers(
    purpose: RetrievalPurpose,
) -> None:
    results = populated_index().search(request(purpose))

    assert [result.record.record_id for result in results] == ["theory:1"]


def test__search__unsupported_purpose_fails_closed() -> None:
    with pytest.raises(
        UnsupportedRetrievalPurposeError,
        match="unsupported retrieval purpose",
    ):
        populated_index().search(
            request(RetrievalPurpose.LITERATURE_REVIEW)
        )


def test__search__requires_record_level_purpose_admission() -> None:
    index = InMemoryRoleScopedChunkIndex(
        admission_policy=course_material_admission_policy()
    )
    index.add_records(
        (
            record(
                "theory:not-admitted",
                "entropy reversible path",
                CorpusRole.THEORY_EVIDENCE,
                1,
                (),
            ),
        )
    )

    assert index.search(request(RetrievalPurpose.PROBLEM_SOLVING)) == ()


def test__search__role_policy_blocks_misadmitted_solution() -> None:
    index = InMemoryRoleScopedChunkIndex(
        admission_policy=course_material_admission_policy()
    )
    index.add_records(
        (
            record(
                "reviewed:misadmitted",
                "entropy reversible path",
                CorpusRole.REVIEWED_SOLUTION,
                1,
                (RetrievalPurpose.PROBLEM_SOLVING,),
            ),
        )
    )

    assert index.search(request(RetrievalPurpose.PROBLEM_SOLVING)) == ()


def test__search__honors_excluded_record_identities() -> None:
    results = populated_index().search(
        request(
            RetrievalPurpose.PROBLEM_SOLVING,
            excluded=("theory:1",),
        )
    )

    assert results == ()


def test__search__uses_record_identity_as_deterministic_tie_break() -> None:
    index = InMemoryRoleScopedChunkIndex(
        admission_policy=course_material_admission_policy()
    )
    index.add_records(
        (
            record(
                "theory:b",
                "entropy path",
                CorpusRole.THEORY_EVIDENCE,
                1,
                (RetrievalPurpose.PROBLEM_SOLVING,),
            ),
            record(
                "theory:a",
                "entropy path",
                CorpusRole.THEORY_EVIDENCE,
                2,
                (RetrievalPurpose.PROBLEM_SOLVING,),
            ),
        )
    )

    results = index.search(request(RetrievalPurpose.PROBLEM_SOLVING))

    assert [result.record.record_id for result in results] == [
        "theory:a",
        "theory:b",
    ]
    assert [result.rank for result in results] == [1, 2]


def test__add_records__rejects_identity_collision() -> None:
    index = InMemoryRoleScopedChunkIndex(
        admission_policy=course_material_admission_policy()
    )
    item = record(
        "theory:1",
        "entropy",
        CorpusRole.THEORY_EVIDENCE,
        1,
        (RetrievalPurpose.PROBLEM_SOLVING,),
    )
    index.add_records((item,))

    with pytest.raises(ValueError, match="already exists"):
        index.add_records((item,))


def test__request__requires_an_explicit_purpose() -> None:
    with pytest.raises(ValueError, match="purpose"):
        RoleScopedSearchRequest(
            query="entropy",
            purpose="problem_solving",  # type: ignore[arg-type]
            excluded_record_ids=(),
            limit=1,
        )


def test__index__requires_an_explicit_admission_policy() -> None:
    with pytest.raises(TypeError, match="admission_policy"):
        InMemoryRoleScopedChunkIndex()  # type: ignore[call-arg]


def test__service__preserves_purpose_scoped_request() -> None:
    service = RoleScopedSearchService(populated_index())

    results = service.search(request(RetrievalPurpose.PROBLEM_SOLVING))

    assert len(results) == 1
    assert results[0].record.record_id == "theory:1"

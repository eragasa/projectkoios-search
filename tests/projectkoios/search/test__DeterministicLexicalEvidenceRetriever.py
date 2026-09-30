from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError, fields, replace

import pytest
from projectkoios.base import (
    DataObjectActionizer,
    DataObjectActionRequest,
    DataObjectActionResult,
    DataObjectModel,
)
from projectkoios.search import (
    AuthoringCorpusRole,
    AuthoringPurpose,
    DeterministicLexicalEvidenceRetriever,
    EvidenceItem,
    EvidenceRetrievalOutcome,
    EvidenceRetrievalRequest,
    EvidenceRetrievalResult,
    EvidenceWarning,
    RankedEvidenceItem,
    ReferenceIdentityStatus,
)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _item(
    *,
    work: str = "work:alpha",
    marker: str = "a",
    indexed_text: str = "entropy reversible path",
    retained_text: str | None = None,
    status: ReferenceIdentityStatus = ReferenceIdentityStatus.CANDIDATE,
    citekey: str | None = None,
    warnings: tuple[EvidenceWarning, ...] = (),
    corpus_role: object = AuthoringCorpusRole.REFERENCE_EVIDENCE,
    source_spans: tuple[str, ...] | None = None,
) -> EvidenceItem:
    retained: str = retained_text or indexed_text
    spans: tuple[str, ...] = source_spans or (f"span:{marker}:1",)
    return EvidenceItem(
        corpus_role=corpus_role,  # type: ignore[arg-type]
        bibliographic_work_id=work,
        reference_identity_status=status,
        accepted_citekey=citekey,
        source_asset_id=f"asset:{work}:{marker}",
        transcript_id=f"transcript:{work}:{marker}",
        page_id=f"page:{marker}",
        page_index=0,
        printed_page_label="1",
        block_id=f"block:{marker}",
        source_span_ids=spans,
        indexed_text=indexed_text,
        indexed_text_sha256=_digest(indexed_text),
        retained_text=retained,
        retained_text_sha256=_digest(retained),
        warnings=warnings,
    )


def _query(
    *,
    query: str = "entropy reversible path",
    bibliographic_work_ids: tuple[str, ...] = (),
    required_works: tuple[str, ...] = (),
    result_limit: int = 10,
    per_work_limit: int = 2,
    max_total_text_characters: int = 10_000,
) -> EvidenceRetrievalRequest:
    return EvidenceRetrievalRequest(
        purpose=AuthoringPurpose.MANUSCRIPT_AUTHORING,
        query=query,
        target_id="target:opaque:revision",
        bibliographic_work_ids=bibliographic_work_ids,
        required_bibliographic_work_ids=required_works,
        result_limit=result_limit,
        per_work_limit=per_work_limit,
        max_total_text_characters=max_total_text_characters,
    )


def _retriever(
    *items: EvidenceItem,
    corpus_id: str = "corpus:authoring:test",
) -> DeterministicLexicalEvidenceRetriever:
    return DeterministicLexicalEvidenceRetriever(
        corpus_id=corpus_id,
        items=tuple(items),
    )


def _evidence_item_id_for(*, item: EvidenceItem) -> str:
    return EvidenceItem.identity_for(
        corpus_role=item.corpus_role,
        bibliographic_work_id=item.bibliographic_work_id,
        reference_identity_status=item.reference_identity_status,
        accepted_citekey=item.accepted_citekey,
        source_asset_id=item.source_asset_id,
        transcript_id=item.transcript_id,
        page_id=item.page_id,
        page_index=item.page_index,
        printed_page_label=item.printed_page_label,
        block_id=item.block_id,
        source_span_ids=item.source_span_ids,
        indexed_text=item.indexed_text,
        indexed_text_sha256=item.indexed_text_sha256,
        retained_text=item.retained_text,
        retained_text_sha256=item.retained_text_sha256,
        warnings=item.warnings,
    )


def _request_id_for(*, request: EvidenceRetrievalRequest) -> str:
    return EvidenceRetrievalRequest.identity_for(
        purpose=request.purpose,
        query=request.query,
        target_id=request.target_id,
        bibliographic_work_ids=request.bibliographic_work_ids,
        required_bibliographic_work_ids=(
            request.required_bibliographic_work_ids
        ),
        result_limit=request.result_limit,
        per_work_limit=request.per_work_limit,
        max_total_text_characters=request.max_total_text_characters,
    )


def _result_id_for(*, result: EvidenceRetrievalResult) -> str:
    return EvidenceRetrievalResult.identity_for(
        request=result.request,
        retriever_implementation_identity=(
            result.retriever_implementation_identity
        ),
        corpus_id=result.corpus_id,
        index_id=result.index_id,
        normalized_query_terms=result.normalized_query_terms,
        outcome=result.outcome,
        evidence=result.evidence,
        candidate_count=result.candidate_count,
        omitted_by_per_work_limit=result.omitted_by_per_work_limit,
        omitted_by_result_limit=result.omitted_by_result_limit,
        omitted_by_aggregate_text_limit=(
            result.omitted_by_aggregate_text_limit
        ),
        omitted_by_required_work=result.omitted_by_required_work,
        missing_required_bibliographic_work_ids=(
            result.missing_required_bibliographic_work_ids
        ),
        warnings=result.warnings,
    )


def test__evidence_item__has_stable_content_derived_identity() -> None:
    first = _item()
    second = _item()
    changed = _item(retained_text="entropy along a reversible path")

    assert first.evidence_item_id == second.evidence_item_id
    assert first.evidence_item_id == _evidence_item_id_for(item=first)
    assert first.evidence_item_id.startswith("evidence-item:sha256:")
    assert first.evidence_item_id != changed.evidence_item_id


def test__evidence_item__ordered_source_spans_affect_identity() -> None:
    first = _item(source_spans=("span:1", "span:2"))
    reversed_item = _item(source_spans=("span:2", "span:1"))

    assert first.evidence_item_id != reversed_item.evidence_item_id


def test__evidence_item__validates_text_digests() -> None:
    with pytest.raises(ValueError, match="indexed text digest"):
        EvidenceItem(
            corpus_role=AuthoringCorpusRole.REFERENCE_EVIDENCE,
            bibliographic_work_id="work:alpha",
            reference_identity_status=ReferenceIdentityStatus.CANDIDATE,
            accepted_citekey=None,
            source_asset_id="asset:alpha",
            transcript_id="transcript:alpha",
            page_id="page:alpha:1",
            page_index=0,
            printed_page_label=None,
            block_id="block:alpha:1",
            source_span_ids=("span:alpha:1",),
            indexed_text="entropy",
            indexed_text_sha256="0" * 64,
            retained_text="entropy",
            retained_text_sha256=_digest("entropy"),
            warnings=(),
        )


def test__evidence_item__preserves_reference_identity_status_and_citekey() -> (
    None
):
    accepted = _item(
        status=ReferenceIdentityStatus.ACCEPTED,
        citekey="Example1965",
    )

    assert accepted.accepted_citekey == "Example1965"

    with pytest.raises(ValueError, match="only an accepted reference"):
        _item(
            status=ReferenceIdentityStatus.CANDIDATE,
            citekey="Proposed1965",
        )


def test__evidence_item__rejects_non_reference_corpus_roles() -> None:
    with pytest.raises(ValueError, match="reference_evidence"):
        _item(corpus_role="manuscript")


@pytest.mark.parametrize(
    ("replacement", "message"),
    (
        (
            {"indexed_text": "x" * 20_001},
            "indexed text must contain",
        ),
        (
            {"source_span_ids": tuple(f"span:{index}" for index in range(33))},
            "1 to 32 source spans",
        ),
        (
            {
                "warnings": tuple(
                    EvidenceWarning(code=f"W{index}", detail="detail")
                    for index in range(33)
                )
            },
            "at most 32 warnings",
        ),
    ),
)
def test__evidence_item__enforces_hard_bounds(
    replacement: dict[str, object],
    message: str,
) -> None:
    values: dict[str, object] = {
        model_field.name: getattr(_item(), model_field.name)
        for model_field in fields(EvidenceItem)
        if model_field.init
    }
    values.update(replacement)
    if "indexed_text" in replacement:
        values["indexed_text_sha256"] = _digest(
            str(replacement["indexed_text"])
        )

    with pytest.raises(ValueError, match=message):
        EvidenceItem(**values)  # type: ignore[arg-type]


def test__evidence_family__is_frozen_and_query_contains_no_target_bytes() -> (
    None
):
    item = _item()

    with pytest.raises(FrozenInstanceError):
        item.indexed_text = "changed"  # type: ignore[misc]

    query_fields = {field.name for field in fields(EvidenceRetrievalRequest)}
    assert "target_text" not in query_fields
    assert "target_context" not in query_fields
    assert "target_id" in query_fields


def test__evidence_query__requires_explicit_manuscript_purpose() -> None:
    with pytest.raises(ValueError, match="manuscript_authoring"):
        EvidenceRetrievalRequest(
            purpose="lecture_authoring",  # type: ignore[arg-type]
            query="entropy",
            target_id="target:opaque",
            bibliographic_work_ids=(),
            required_bibliographic_work_ids=(),
            result_limit=1,
            per_work_limit=1,
            max_total_text_characters=100,
        )


def test__evidence_query__enforces_bounds_and_filter_relationships() -> None:
    with pytest.raises(ValueError, match="query must contain"):
        _query(query="x" * 2_001)
    with pytest.raises(ValueError, match="result limit"):
        _query(result_limit=51)
    with pytest.raises(ValueError, match="cannot exceed"):
        _query(result_limit=1, per_work_limit=2)
    with pytest.raises(ValueError, match="included in work filters"):
        _query(
            bibliographic_work_ids=("work:alpha",),
            required_works=("work:beta",),
        )
    with pytest.raises(ValueError, match="at most 32 items"):
        _query(
            bibliographic_work_ids=tuple(f"work:{index}" for index in range(33))
        )
    with pytest.raises(ValueError, match="aggregate text limit"):
        _query(max_total_text_characters=100_001)


def test__evidence_bounds__accept_edges_and_reject_overflow() -> None:
    edge_warning = EvidenceWarning(
        code="W" * EvidenceWarning.MAX_CODE_CHARACTERS,
        detail="d" * EvidenceWarning.MAX_DETAIL_CHARACTERS,
    )
    edge_query = _query(
        query="q" * EvidenceRetrievalRequest.MAX_QUERY_CHARACTERS
    )

    assert len(edge_warning.code) == EvidenceWarning.MAX_CODE_CHARACTERS
    assert edge_warning.warning_id == EvidenceWarning.identity_for(
        code=edge_warning.code,
        detail=edge_warning.detail,
    )
    assert (
        len(edge_query.query) == EvidenceRetrievalRequest.MAX_QUERY_CHARACTERS
    )
    assert edge_query.request_id == _request_id_for(request=edge_query)

    with pytest.raises(ValueError, match="warning detail"):
        EvidenceWarning(
            code="WARNING",
            detail="d" * (EvidenceWarning.MAX_DETAIL_CHARACTERS + 1),
        )
    with pytest.raises(ValueError, match="retained text must contain"):
        _item(
            retained_text=(
                "r" * (EvidenceItem.MAX_RETAINED_TEXT_CHARACTERS + 1)
            )
        )


def test__retriever__uses_canonical_taxonomy_identities_and_action() -> None:
    item = _item()
    request = _query()
    retriever = _retriever(item)

    retrieved = retriever.retrieve(request=request)
    action_result = retriever.action(request=request)
    ranked = retrieved.evidence[0]

    assert issubclass(EvidenceWarning, DataObjectModel)
    assert issubclass(EvidenceItem, DataObjectModel)
    assert issubclass(EvidenceRetrievalRequest, DataObjectActionRequest)
    assert issubclass(RankedEvidenceItem, DataObjectModel)
    assert issubclass(EvidenceRetrievalResult, DataObjectActionResult)
    assert issubclass(
        DeterministicLexicalEvidenceRetriever,
        DataObjectActionizer,
    )
    assert action_result == retrieved
    assert retrieved.request is request
    assert request.request_id == _request_id_for(request=request)
    assert ranked.ranked_evidence_item_id == RankedEvidenceItem.identity_for(
        evidence_item_id=ranked.item.evidence_item_id,
        score=ranked.score,
        rank=ranked.rank,
        matched_terms=ranked.matched_terms,
        tie_key=ranked.tie_key,
    )
    assert retrieved.result_id == _result_id_for(result=retrieved)
    assert retrieved.result_id != request.request_id
    assert not next(
        item for item in fields(EvidenceWarning) if item.name == "warning_id"
    ).init
    assert not next(
        item for item in fields(EvidenceItem) if item.name == "evidence_item_id"
    ).init
    assert not next(
        item
        for item in fields(EvidenceRetrievalRequest)
        if item.name == "request_id"
    ).init
    assert not next(
        item
        for item in fields(RankedEvidenceItem)
        if item.name == "ranked_evidence_item_id"
    ).init
    assert not next(
        item
        for item in fields(EvidenceRetrievalResult)
        if item.name == "result_id"
    ).init


def test__retriever__returns_ranked_source_linked_evidence() -> None:
    warning = EvidenceWarning(code="GLYPH_UNCERTAIN", detail="inspect page")
    high = _item(
        work="work:alpha",
        marker="high",
        indexed_text="entropy entropy reversible path",
        warnings=(warning,),
    )
    low = _item(
        work="work:beta",
        marker="low",
        indexed_text="entropy path",
    )

    result = _retriever(high, low).retrieve(request=_query())

    assert result.outcome is EvidenceRetrievalOutcome.EVIDENCE_AVAILABLE
    assert [entry.rank for entry in result.evidence] == [1, 2]
    assert result.evidence[0].score >= result.evidence[1].score
    assert all(
        entry.tie_key == entry.item.evidence_item_id
        for entry in result.evidence
    )
    assert result.evidence[0].matched_terms
    assert result.warnings == ("GLYPH_UNCERTAIN",)
    assert result.evidence[0].item.warnings == (warning,)


def test__retriever__is_deterministic_across_input_order() -> None:
    items = (
        _item(work="work:alpha", marker="a", indexed_text="entropy path"),
        _item(work="work:beta", marker="b", indexed_text="entropy path"),
    )
    forward = _retriever(*items)
    reverse = _retriever(*reversed(items))

    forward_result = forward.retrieve(request=_query())
    reverse_result = reverse.retrieve(request=_query())

    assert forward.index_id == reverse.index_id
    assert forward_result == reverse_result
    assert [
        entry.item.evidence_item_id for entry in forward_result.evidence
    ] == sorted(item.evidence_item_id for item in items)


def test__retriever__uses_global_rank_then_per_work_diversity() -> None:
    items = (
        _item(
            work="work:alpha",
            marker="a1",
            indexed_text="entropy entropy reversible path",
        ),
        _item(
            work="work:alpha",
            marker="a2",
            indexed_text="entropy reversible path",
        ),
        _item(
            work="work:beta",
            marker="b1",
            indexed_text="entropy reversible path",
        ),
    )
    retriever = _retriever(*items)
    unrestricted = retriever.retrieve(
        request=_query(result_limit=3, per_work_limit=3)
    )
    diverse = retriever.retrieve(
        request=_query(result_limit=3, per_work_limit=1)
    )

    assert diverse.evidence[0].item == unrestricted.evidence[0].item
    assert {entry.item.bibliographic_work_id for entry in diverse.evidence} == {
        "work:alpha",
        "work:beta",
    }
    assert diverse.omitted_by_per_work_limit == 1
    assert diverse.truncated


def test__retriever__records_result_and_aggregate_omissions() -> None:
    items = tuple(
        _item(
            work=f"work:{marker}",
            marker=marker,
            indexed_text="entropy reversible path",
        )
        for marker in ("a", "b", "c")
    )
    retriever = _retriever(*items)
    result_limited = retriever.retrieve(
        request=_query(result_limit=1, per_work_limit=1)
    )
    strongest = result_limited.evidence[0].item
    aggregate_limited = retriever.retrieve(
        request=_query(
            result_limit=3,
            per_work_limit=1,
            max_total_text_characters=strongest.result_text_characters,
        )
    )

    assert result_limited.omitted_by_result_limit == 2
    assert aggregate_limited.evidence[0].item == strongest
    assert aggregate_limited.omitted_by_aggregate_text_limit == 2
    assert aggregate_limited.selected_text_characters == (
        strongest.result_text_characters
    )


def test__retriever__applies_bounded_bibliographic_work_ids() -> None:
    alpha = _item(work="work:alpha", marker="a")
    beta = _item(work="work:beta", marker="b")

    result = _retriever(alpha, beta).retrieve(
        request=_query(bibliographic_work_ids=("work:beta",))
    )

    assert [entry.item for entry in result.evidence] == [beta]


def test__retriever__reports_missing_required_work_without_substitution() -> (
    None
):
    alpha = _item(work="work:alpha", marker="a")

    result = _retriever(alpha).retrieve(
        request=_query(
            bibliographic_work_ids=("work:alpha", "work:missing"),
            required_works=("work:missing",),
        )
    )

    assert result.outcome is EvidenceRetrievalOutcome.INSUFFICIENT_EVIDENCE
    assert result.evidence == ()
    assert result.missing_required_bibliographic_work_ids == ("work:missing",)
    assert result.omitted_by_required_work == 1


def test__retriever__does_not_substitute_when_bounds_omit_required_work() -> (
    None
):
    strongest = _item(
        work="work:alpha",
        marker="a",
        indexed_text="entropy entropy reversible path",
    )
    required = _item(
        work="work:beta",
        marker="b",
        indexed_text="entropy path",
    )

    result = _retriever(strongest, required).retrieve(
        request=_query(
            bibliographic_work_ids=("work:alpha", "work:beta"),
            required_works=("work:beta",),
            result_limit=1,
            per_work_limit=1,
        )
    )

    assert result.outcome is EvidenceRetrievalOutcome.INSUFFICIENT_EVIDENCE
    assert result.evidence == ()
    assert result.missing_required_bibliographic_work_ids == ("work:beta",)
    assert result.omitted_by_required_work == 2


def test__retriever__distinguishes_zero_hits_from_invalid_query() -> None:
    retriever = _retriever(_item())

    insufficient = retriever.retrieve(request=_query(query="superconductivity"))
    invalid = retriever.retrieve(request=_query(query="--- ___"))

    assert (
        insufficient.outcome is EvidenceRetrievalOutcome.INSUFFICIENT_EVIDENCE
    )
    assert insufficient.warnings == ()
    assert invalid.outcome is EvidenceRetrievalOutcome.INVALID_REQUEST
    assert invalid.warnings == ("QUERY_HAS_NO_LEXICAL_TERMS",)


def test__retriever__rejects_queries_beyond_lexical_term_bound() -> None:
    query_text = " ".join(
        f"t{index}"
        for index in range(EvidenceRetrievalRequest.MAX_QUERY_TERMS + 1)
    )

    result = _retriever(_item()).retrieve(request=_query(query=query_text))

    assert result.outcome is EvidenceRetrievalOutcome.INVALID_REQUEST
    assert result.warnings == ("QUERY_EXCEEDS_LEXICAL_TERM_LIMIT",)


def test__result__keeps_infrastructure_failure_distinct() -> None:
    request = _query()
    failure = EvidenceRetrievalResult(
        request=request,
        retriever_implementation_identity=(
            DeterministicLexicalEvidenceRetriever.IMPLEMENTATION_IDENTITY
        ),
        corpus_id="corpus:authoring:test",
        index_id="index:unavailable",
        normalized_query_terms=("entropy",),
        outcome=EvidenceRetrievalOutcome.INFRASTRUCTURE_FAILURE,
        evidence=(),
        candidate_count=0,
        omitted_by_per_work_limit=0,
        omitted_by_result_limit=0,
        omitted_by_aggregate_text_limit=0,
        omitted_by_required_work=0,
        missing_required_bibliographic_work_ids=(),
        warnings=("INDEX_UNAVAILABLE",),
    )

    assert failure.outcome is EvidenceRetrievalOutcome.INFRASTRUCTURE_FAILURE
    assert failure.outcome is not EvidenceRetrievalOutcome.INSUFFICIENT_EVIDENCE


def test__result__rejects_evidence_for_nonavailable_outcome() -> None:
    available = _retriever(_item()).retrieve(request=_query())

    with pytest.raises(ValueError, match="exactly when"):
        replace(
            available,
            outcome=EvidenceRetrievalOutcome.INSUFFICIENT_EVIDENCE,
        )


def test__retriever__rejects_duplicate_evidence_item_id() -> None:
    item = _item()

    with pytest.raises(ValueError, match="unique evidence item IDs"):
        _retriever(item, item)

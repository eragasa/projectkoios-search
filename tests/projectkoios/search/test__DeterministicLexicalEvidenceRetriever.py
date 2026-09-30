from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError, fields, replace

import pytest
from projectkoios.base import DataObjectActionizer
from projectkoios.search import (
    AuthoringCorpusRole,
    AuthoringPurpose,
    DeterministicLexicalEvidenceRetriever,
    EvidenceBundle,
    EvidenceItem,
    EvidenceQuery,
    EvidenceRetrievalOutcome,
    EvidenceWarning,
    ReferenceAuthorityStatus,
)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _item(
    *,
    work: str = "work:alpha",
    marker: str = "a",
    indexed_text: str = "entropy reversible path",
    retained_text: str | None = None,
    status: ReferenceAuthorityStatus = ReferenceAuthorityStatus.CANDIDATE,
    citekey: str | None = None,
    warnings: tuple[EvidenceWarning, ...] = (),
    corpus_role: object = AuthoringCorpusRole.REFERENCE_EVIDENCE,
    source_spans: tuple[str, ...] | None = None,
) -> EvidenceItem:
    retained: str = retained_text or indexed_text
    spans: tuple[str, ...] = source_spans or (f"span:{marker}:1",)
    return EvidenceItem(
        corpus_role=corpus_role,  # type: ignore[arg-type]
        bibliographic_work_identity=work,
        reference_status=status,
        accepted_citekey=citekey,
        source_asset_identity=f"asset:{work}:{marker}",
        transcript_identity=f"transcript:{work}:{marker}",
        page_identity=f"page:{marker}",
        page_index=0,
        printed_page_label="1",
        block_identity=f"block:{marker}",
        source_span_identities=spans,
        indexed_text=indexed_text,
        indexed_text_sha256=_digest(indexed_text),
        retained_text=retained,
        retained_text_sha256=_digest(retained),
        warnings=warnings,
    )


def _query(
    *,
    query: str = "entropy reversible path",
    work_filters: tuple[str, ...] = (),
    required_works: tuple[str, ...] = (),
    result_limit: int = 10,
    per_work_limit: int = 2,
    max_total_text_characters: int = 10_000,
) -> EvidenceQuery:
    return EvidenceQuery(
        purpose=AuthoringPurpose.MANUSCRIPT_AUTHORING,
        query=query,
        target_identity="target:opaque:revision",
        work_filters=work_filters,
        required_work_identities=required_works,
        result_limit=result_limit,
        per_work_limit=per_work_limit,
        max_total_text_characters=max_total_text_characters,
    )


def _retriever(
    *items: EvidenceItem,
    corpus_identity: str = "corpus:authoring:test",
) -> DeterministicLexicalEvidenceRetriever:
    return DeterministicLexicalEvidenceRetriever(
        corpus_identity=corpus_identity,
        items=tuple(items),
    )


def test__evidence_item__has_stable_content_derived_identity() -> None:
    first = _item()
    second = _item()
    changed = _item(retained_text="entropy along a reversible path")

    assert first.identity == second.identity
    assert first.identity.startswith("evidence-item:sha256:")
    assert first.identity != changed.identity


def test__evidence_item__ordered_source_spans_affect_identity() -> None:
    first = _item(source_spans=("span:1", "span:2"))
    reversed_item = _item(source_spans=("span:2", "span:1"))

    assert first.identity != reversed_item.identity


def test__evidence_item__validates_text_digests() -> None:
    with pytest.raises(ValueError, match="indexed text digest"):
        EvidenceItem(
            corpus_role=AuthoringCorpusRole.REFERENCE_EVIDENCE,
            bibliographic_work_identity="work:alpha",
            reference_status=ReferenceAuthorityStatus.CANDIDATE,
            accepted_citekey=None,
            source_asset_identity="asset:alpha",
            transcript_identity="transcript:alpha",
            page_identity="page:alpha:1",
            page_index=0,
            printed_page_label=None,
            block_identity="block:alpha:1",
            source_span_identities=("span:alpha:1",),
            indexed_text="entropy",
            indexed_text_sha256="0" * 64,
            retained_text="entropy",
            retained_text_sha256=_digest("entropy"),
            warnings=(),
        )


def test__evidence_item__preserves_reference_authority_and_citekey() -> None:
    accepted = _item(
        status=ReferenceAuthorityStatus.ACCEPTED,
        citekey="Example1965",
    )

    assert accepted.accepted_citekey == "Example1965"

    with pytest.raises(ValueError, match="only an accepted reference"):
        _item(
            status=ReferenceAuthorityStatus.CANDIDATE,
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
            {
                "source_span_identities": tuple(
                    f"span:{index}" for index in range(33)
                )
            },
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
        field.name: getattr(_item(), field.name)
        for field in fields(EvidenceItem)
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

    query_fields = {field.name for field in fields(EvidenceQuery)}
    assert "target_text" not in query_fields
    assert "target_context" not in query_fields
    assert "target_identity" in query_fields


def test__evidence_query__requires_explicit_manuscript_purpose() -> None:
    with pytest.raises(ValueError, match="manuscript_authoring"):
        EvidenceQuery(
            purpose="lecture_authoring",  # type: ignore[arg-type]
            query="entropy",
            target_identity="target:opaque",
            work_filters=(),
            required_work_identities=(),
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
            work_filters=("work:alpha",),
            required_works=("work:beta",),
        )
    with pytest.raises(ValueError, match="at most 32 items"):
        _query(work_filters=tuple(f"work:{index}" for index in range(33)))
    with pytest.raises(ValueError, match="aggregate text limit"):
        _query(max_total_text_characters=100_001)


def test__evidence_bounds__accept_edges_and_reject_overflow() -> None:
    edge_warning = EvidenceWarning(
        code="W" * EvidenceWarning.MAX_CODE_CHARACTERS,
        detail="d" * EvidenceWarning.MAX_DETAIL_CHARACTERS,
    )
    edge_query = _query(query="q" * EvidenceQuery.MAX_QUERY_CHARACTERS)

    assert len(edge_warning.code) == EvidenceWarning.MAX_CODE_CHARACTERS
    assert len(edge_query.query) == EvidenceQuery.MAX_QUERY_CHARACTERS

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


def test__retriever__directly_implements_data_object_actionizer() -> None:
    retriever = _retriever(_item())

    assert isinstance(retriever, DataObjectActionizer)
    assert retriever.action(request=_query()) == retriever.retrieve(
        request=_query()
    )


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

    bundle = _retriever(high, low).retrieve(request=_query())

    assert bundle.outcome is EvidenceRetrievalOutcome.EVIDENCE_AVAILABLE
    assert [entry.rank for entry in bundle.evidence] == [1, 2]
    assert bundle.evidence[0].score >= bundle.evidence[1].score
    assert all(
        entry.tie_key == entry.item.identity for entry in bundle.evidence
    )
    assert bundle.evidence[0].matched_terms
    assert bundle.warnings == ("GLYPH_UNCERTAIN",)
    assert bundle.evidence[0].item.warnings == (warning,)


def test__retriever__is_deterministic_across_input_order() -> None:
    items = (
        _item(work="work:alpha", marker="a", indexed_text="entropy path"),
        _item(work="work:beta", marker="b", indexed_text="entropy path"),
    )
    forward = _retriever(*items)
    reverse = _retriever(*reversed(items))

    forward_bundle = forward.retrieve(request=_query())
    reverse_bundle = reverse.retrieve(request=_query())

    assert forward.index_identity == reverse.index_identity
    assert forward_bundle == reverse_bundle
    assert [entry.item.identity for entry in forward_bundle.evidence] == sorted(
        item.identity for item in items
    )


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
    assert {
        entry.item.bibliographic_work_identity for entry in diverse.evidence
    } == {"work:alpha", "work:beta"}
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
            max_total_text_characters=strongest.bundle_text_characters,
        )
    )

    assert result_limited.omitted_by_result_limit == 2
    assert aggregate_limited.evidence[0].item == strongest
    assert aggregate_limited.omitted_by_aggregate_text_limit == 2
    assert aggregate_limited.selected_text_characters == (
        strongest.bundle_text_characters
    )


def test__retriever__applies_bounded_work_filters() -> None:
    alpha = _item(work="work:alpha", marker="a")
    beta = _item(work="work:beta", marker="b")

    bundle = _retriever(alpha, beta).retrieve(
        request=_query(work_filters=("work:beta",))
    )

    assert [entry.item for entry in bundle.evidence] == [beta]


def test__retriever__reports_missing_required_work_without_substitution() -> (
    None
):
    alpha = _item(work="work:alpha", marker="a")

    bundle = _retriever(alpha).retrieve(
        request=_query(
            work_filters=("work:alpha", "work:missing"),
            required_works=("work:missing",),
        )
    )

    assert bundle.outcome is EvidenceRetrievalOutcome.INSUFFICIENT_EVIDENCE
    assert bundle.evidence == ()
    assert bundle.missing_required_work_identities == ("work:missing",)
    assert bundle.omitted_by_required_work == 1


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

    bundle = _retriever(strongest, required).retrieve(
        request=_query(
            work_filters=("work:alpha", "work:beta"),
            required_works=("work:beta",),
            result_limit=1,
            per_work_limit=1,
        )
    )

    assert bundle.outcome is EvidenceRetrievalOutcome.INSUFFICIENT_EVIDENCE
    assert bundle.evidence == ()
    assert bundle.missing_required_work_identities == ("work:beta",)
    assert bundle.omitted_by_required_work == 2


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
        f"t{index}" for index in range(EvidenceQuery.MAX_QUERY_TERMS + 1)
    )

    bundle = _retriever(_item()).retrieve(request=_query(query=query_text))

    assert bundle.outcome is EvidenceRetrievalOutcome.INVALID_REQUEST
    assert bundle.warnings == ("QUERY_EXCEEDS_LEXICAL_TERM_LIMIT",)


def test__bundle__keeps_infrastructure_failure_distinct() -> None:
    request = _query()
    failure = EvidenceBundle(
        request=request,
        corpus_identity="corpus:authoring:test",
        index_identity="index:unavailable",
        normalized_query_terms=("entropy",),
        outcome=EvidenceRetrievalOutcome.INFRASTRUCTURE_FAILURE,
        evidence=(),
        candidate_count=0,
        omitted_by_per_work_limit=0,
        omitted_by_result_limit=0,
        omitted_by_aggregate_text_limit=0,
        omitted_by_required_work=0,
        missing_required_work_identities=(),
        warnings=("INDEX_UNAVAILABLE",),
    )

    assert failure.outcome is EvidenceRetrievalOutcome.INFRASTRUCTURE_FAILURE
    assert failure.outcome is not EvidenceRetrievalOutcome.INSUFFICIENT_EVIDENCE


def test__bundle__rejects_evidence_for_nonavailable_outcome() -> None:
    available = _retriever(_item()).retrieve(request=_query())

    with pytest.raises(ValueError, match="exactly when"):
        replace(
            available,
            outcome=EvidenceRetrievalOutcome.INSUFFICIENT_EVIDENCE,
        )


def test__retriever__rejects_duplicate_evidence_identity() -> None:
    item = _item()

    with pytest.raises(ValueError, match="unique identities"):
        _retriever(item, item)

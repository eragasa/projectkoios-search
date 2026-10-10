"""Contract tests for deterministic page-projection lexical tokenization.

The tokenizer is backend-neutral and versioned because its exact output enters
corpus and index identities persisted by storage adapters.
"""

from __future__ import annotations

import pytest
from projectkoios.search.page_projection_lexical import (
    PageProjectionLexicalTokenizer,
)


def test__tokens__are_unicode_casefolded_and_repeatable() -> None:
    """Preserve deterministic Unicode, punctuation, and repetition behavior.

    Notes
    -----
    Repeated document terms remain repeated for BM25 term frequency, while
    underscore is a delimiter rather than a lexical character.
    """

    tokenizer = PageProjectionLexicalTokenizer()
    text = "Alpha α.alpha co-op _drop ALPHA"

    first = tokenizer.tokens(text=text)
    second = tokenizer.tokens(text=text)

    assert first == ("alpha", "α.alpha", "co-op", "drop", "alpha")
    assert second == first
    assert tokenizer.IMPLEMENTATION_VERSION == "1.0"
    assert tokenizer.tokenizer_id == (
        "projectkoios.search.page-projection-lexical-tokenizer:1.0"
    )


def test__query_terms__deduplicate_in_first_seen_order() -> None:
    """Deduplicate query terms without sorting away caller term order."""

    tokenizer = PageProjectionLexicalTokenizer()

    assert tokenizer.query_terms(text="Beta alpha beta gamma") == (
        "beta",
        "alpha",
        "gamma",
    )


def test__tokens__reject_invalid_or_unbounded_text() -> None:
    """Reject non-text, blank, and over-limit tokenization inputs."""

    tokenizer = PageProjectionLexicalTokenizer()

    with pytest.raises(TypeError, match="built-in string"):
        tokenizer.tokens(text=object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="nonblank"):
        tokenizer.tokens(text="   ")
    with pytest.raises(ValueError, match="byte limit"):
        tokenizer.tokens(text="a" * (tokenizer.MAXIMUM_TEXT_BYTES + 1))

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable

from projectkoios.search.models import (
    RoleScopedChunk,
    RoleScopedChunkSearchResult,
    RoleScopedSearchRequest,
)


class InMemoryRoleScopedChunkIndex:
    """Small deterministic BM25 index with explicit corpus roles."""

    def __init__(self) -> None:
        self._records: dict[str, RoleScopedChunk] = {}

    def add_records(self, records: Iterable[RoleScopedChunk]) -> None:
        pending = tuple(records)
        identities = tuple(record.record_id for record in pending)
        if len(set(identities)) != len(identities):
            raise ValueError("input contains duplicate record identities")
        collisions = set(identities) & set(self._records)
        if collisions:
            raise ValueError("record identity already exists")
        self._records.update((record.record_id, record) for record in pending)

    def search(
        self,
        request: RoleScopedSearchRequest,
    ) -> tuple[RoleScopedChunkSearchResult, ...]:
        terms = tuple(dict.fromkeys(self._terms(request.query)))
        allowed = set(request.allowed_roles)
        excluded = set(request.excluded_record_ids)
        admitted = tuple(
            record
            for record in self._records.values()
            if record.corpus_role in allowed
            and record.record_id not in excluded
        )
        document_terms = {
            record.record_id: self._terms(record.chunk.text)
            for record in admitted
        }
        average_length = (
            sum(len(terms_) for terms_ in document_terms.values())
            / len(document_terms)
            if document_terms
            else 0.0
        )
        frequencies = {
            term: sum(
                term in document_terms[record.record_id] for record in admitted
            )
            for term in terms
        }
        scored: list[tuple[RoleScopedChunk, float]] = []
        for record in admitted:
            terms_ = document_terms[record.record_id]
            score = self._bm25_score(
                terms,
                Counter(terms_),
                len(terms_),
                len(admitted),
                frequencies,
                average_length,
            )
            if score > 0:
                scored.append((record, score))
        scored.sort(key=lambda item: (-item[1], item[0].record_id))
        return tuple(
            RoleScopedChunkSearchResult(
                record=record,
                score=score,
                rank=rank,
            )
            for rank, (record, score) in enumerate(
                scored[: request.limit],
                start=1,
            )
        )

    @staticmethod
    def _terms(text: str) -> tuple[str, ...]:
        return tuple(
            match.group(0)
            for match in re.finditer(
                r"[0-9a-z]+(?:[.-][0-9a-z]+)*",
                text.casefold(),
            )
        )

    @staticmethod
    def _bm25_score(
        query_terms: tuple[str, ...],
        counts: Counter[str],
        document_length: int,
        document_count: int,
        document_frequencies: dict[str, int],
        average_document_length: float,
    ) -> float:
        if document_count == 0 or average_document_length == 0:
            return 0.0
        k1 = 1.2
        b = 0.75
        score = 0.0
        for term in query_terms:
            term_frequency = counts[term]
            if term_frequency == 0:
                continue
            document_frequency = document_frequencies[term]
            inverse_document_frequency = math.log(
                1.0
                + (document_count - document_frequency + 0.5)
                / (document_frequency + 0.5)
            )
            normalization = term_frequency + k1 * (
                1.0 - b + b * document_length / average_document_length
            )
            score += inverse_document_frequency * (
                term_frequency * (k1 + 1.0) / normalization
            )
        return score

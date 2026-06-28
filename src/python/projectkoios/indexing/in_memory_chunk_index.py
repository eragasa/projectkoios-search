from __future__ import annotations

from collections.abc import Iterable

from projectkoios.chunking import TextChunk
from projectkoios.search.models import ChunkSearchResult


class InMemoryChunkIndex:
    def __init__(self) -> None:
        self._chunks: list[TextChunk] = []

    def add_chunks(self, chunks: Iterable[TextChunk]) -> None:
        self._chunks.extend(chunks)

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> list[ChunkSearchResult]:
        if limit <= 0:
            return []

        query_terms = self._query_terms(query)

        if not query_terms:
            return []

        results: list[ChunkSearchResult] = []

        for chunk in self._chunks:
            score = self._score(
                chunk=chunk,
                query_terms=query_terms,
            )

            if score <= 0:
                continue

            results.append(
                ChunkSearchResult(
                    chunk=chunk,
                    score=float(score),
                )
            )

        results.sort(
            key=lambda result: result.score,
            reverse=True,
        )

        return results[:limit]

    def _query_terms(self, query: str) -> list[str]:
        return [
            term
            for term in query.lower().split()
            if term
        ]

    def _score(
        self,
        *,
        chunk: TextChunk,
        query_terms: list[str],
    ) -> int:
        text = chunk.text.lower()

        return sum(
            1
            for term in query_terms
            if term in text
        )

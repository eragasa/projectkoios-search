from __future__ import annotations

from typing import Protocol

from projectkoios.search.models import ChunkSearchResult


class ChunkSearchIndex(Protocol):
    def search(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> list[ChunkSearchResult]:
        ...

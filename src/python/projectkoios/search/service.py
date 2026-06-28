from __future__ import annotations

from projectkoios.search.models import ChunkSearchResult
from projectkoios.search.protocols import ChunkSearchIndex


class SearchService:
    def __init__(
        self,
        search_index: ChunkSearchIndex,
    ) -> None:
        self.search_index = search_index

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> list[ChunkSearchResult]:
        return self.search_index.search(
            query=query,
            limit=limit,
        )

from __future__ import annotations

from projectkoios.search.models import (
    ChunkSearchResult,
    RoleScopedChunkSearchResult,
    RoleScopedSearchRequest,
)
from projectkoios.search.protocols import (
    ChunkSearchIndex,
    RoleScopedChunkSearchIndex,
)


class RoleScopedSearchService:
    def __init__(self, search_index: RoleScopedChunkSearchIndex) -> None:
        self.search_index = search_index

    def search(
        self,
        request: RoleScopedSearchRequest,
    ) -> tuple[RoleScopedChunkSearchResult, ...]:
        return self.search_index.search(request)


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

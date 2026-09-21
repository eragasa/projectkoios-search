from __future__ import annotations

from typing import Protocol

from projectkoios.search.models import (
    ChunkSearchResult,
    RoleScopedChunkSearchResult,
    RoleScopedSearchRequest,
)


class RoleScopedChunkSearchIndex(Protocol):
    def search(
        self,
        request: RoleScopedSearchRequest,
    ) -> tuple[RoleScopedChunkSearchResult, ...]: ...


class ChunkSearchIndex(Protocol):
    def search(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> list[ChunkSearchResult]: ...

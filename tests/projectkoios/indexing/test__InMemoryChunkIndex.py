# tests/projectkoios/search/test__MemorySearchIndex.py

from pathlib import Path

from projectkoios.chunking import TextChunk
from projectkoios.indexing import InMemoryChunkIndex


def make_chunk(
    text: str,
    *,
    source_path: Path = Path("src/example.py"),
    source_kind: str = "code_file",
    language: str = "python",
    chunk_index: int = 0,
    start_line: int = 1,
    end_line: int = 1,
) -> TextChunk:
    return TextChunk(
        source_path=source_path,
        source_kind=source_kind,
        language=language,
        chunk_index=chunk_index,
        start_line=start_line,
        end_line=end_line,
        text=text,
    )


def test__add_chunks__stores_chunks() -> None:
    index = InMemoryChunkIndex()

    chunk = make_chunk("app = FastAPI()\n")

    index.add_chunks([chunk])

    results = index.search("FastAPI")

    assert len(results) == 1
    assert results[0].chunk == chunk


def test__search__returns_matching_chunks() -> None:
    index = InMemoryChunkIndex()

    matching_chunk = make_chunk("app = FastAPI()\n")
    non_matching_chunk = make_chunk("def unrelated(): pass\n")

    index.add_chunks([matching_chunk, non_matching_chunk])

    results = index.search("FastAPI")

    assert len(results) == 1
    assert results[0].chunk == matching_chunk


def test__search__is_case_insensitive() -> None:
    index = InMemoryChunkIndex()

    chunk = make_chunk("app = FastAPI()\n")

    index.add_chunks([chunk])

    results = index.search("fastapi")

    assert len(results) == 1
    assert results[0].chunk == chunk


def test__search__returns_empty_list_when_no_match() -> None:
    index = InMemoryChunkIndex()

    chunk = make_chunk("app = FastAPI()\n")

    index.add_chunks([chunk])

    results = index.search("Django")

    assert results == []


def test__search__respects_limit() -> None:
    index = InMemoryChunkIndex()

    chunks = [
        make_chunk(
            "FastAPI app\n",
            source_path=Path(f"src/example_{index_}.py"),
            chunk_index=index_,
        )
        for index_ in range(3)
    ]

    index.add_chunks(chunks)

    results = index.search("FastAPI", limit=2)

    assert len(results) == 2


def test__search__preserves_chunk_provenance() -> None:
    index = InMemoryChunkIndex()

    chunk = make_chunk(
        "app = FastAPI()\n",
        source_path=Path("src/projectkoios/api/app.py"),
        source_kind="code_file",
        language="python",
        chunk_index=3,
        start_line=20,
        end_line=40,
    )

    index.add_chunks([chunk])

    results = index.search("FastAPI")

    assert len(results) == 1

    result_chunk = results[0].chunk

    assert result_chunk.source_path == Path("src/projectkoios/api/app.py")
    assert result_chunk.source_kind == "code_file"
    assert result_chunk.language == "python"
    assert result_chunk.chunk_index == 3
    assert result_chunk.start_line == 20
    assert result_chunk.end_line == 40


def test__search__orders_results_by_score() -> None:
    index = InMemoryChunkIndex()

    lower_score_chunk = make_chunk(
        "FastAPI app\n",
        source_path=Path("src/lower.py"),
    )
    higher_score_chunk = make_chunk(
        "FastAPI app router\n",
        source_path=Path("src/higher.py"),
    )

    index.add_chunks([lower_score_chunk, higher_score_chunk])

    results = index.search("FastAPI router")

    assert len(results) == 2
    assert results[0].chunk == higher_score_chunk
    assert results[0].score > results[1].score


def test__search__returns_empty_list_for_empty_query() -> None:
    index = InMemoryChunkIndex()

    chunk = make_chunk("app = FastAPI()\n")

    index.add_chunks([chunk])

    results = index.search("")

    assert results == []


def test__search__returns_empty_list_for_non_positive_limit() -> None:
    index = InMemoryChunkIndex()

    chunk = make_chunk("app = FastAPI()\n")

    index.add_chunks([chunk])

    results = index.search("FastAPI", limit=0)

    assert results == []
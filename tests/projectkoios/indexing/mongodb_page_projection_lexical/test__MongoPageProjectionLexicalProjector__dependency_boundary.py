"""Dependency-boundary tests for the MongoDB lexical adapter."""

from __future__ import annotations

import ast
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
SOURCE_ROOT = REPOSITORY_ROOT / "src/python/projectkoios"
CONTRACT_MODULE = SOURCE_ROOT / "search/page_projection_lexical.py"
ADAPTER_MODULE = SOURCE_ROOT / "indexing/mongodb_page_projection_lexical.py"


def _imports(path: Path) -> tuple[str, ...]:
    """Return direct import targets without executing a source module.

    Parameters
    ----------
    path
        Python source file to parse.

    Returns
    -------
    tuple[str, ...]
        Import targets in abstract-syntax-tree traversal order.
    """

    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            values.append(node.module)
    return tuple(values)


def test__dependency_boundary__never_imports_ingestion() -> None:
    """Keep backend-neutral contracts and Mongo persistence out of Ingestion."""

    imports = (*_imports(CONTRACT_MODULE), *_imports(ADAPTER_MODULE))

    assert not any(
        value.startswith("projectkoios.ingestion") for value in imports
    )


def test__dependency_boundary__uses_only_structural_chunk_contract() -> None:
    """Prevent the Mongo adapter from importing the concrete chunking module.

    Notes
    -----
    The adapter consumes exact chunk outputs through the backend-neutral
    structural contract, avoiding the concrete module's Ingestion leaf import.
    """

    imports = _imports(ADAPTER_MODULE)

    assert "projectkoios.search.page_projection_chunking" not in imports
    assert "projectkoios.search.page_projection_lexical" in imports


def test__dependency_boundary__contains_no_machine_connection_material() -> (
    None
):
    """Reject embedded listener, credential, URI, or machine-path literals."""

    text = ADAPTER_MODULE.read_text(encoding="utf-8")

    assert "127.0.0.1" not in text
    assert "27017" not in text
    assert "27018" not in text
    assert "mongodb://" not in text
    assert "password" not in text.casefold()
    assert "/Users/" not in text

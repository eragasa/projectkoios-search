"""Dependency-boundary tests for :class:`PageProjectionChunker`.

The production dependency is intentionally narrower than the package metadata:
only the chunk-derivation leaf may import Ingestion, while Search indexing,
retrieval, and the package facade remain import-independent.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
SOURCE_ROOT = REPOSITORY_ROOT / "src/python/projectkoios"
CHUNKING_MODULE = SOURCE_ROOT / "search/page_projection_chunking.py"
EXACT_INGESTION_LEAF = "projectkoios.ingestion.page.projection.result"


def _imports(path: Path) -> tuple[str, ...]:
    """Return every direct import target declared by one Python source file.

    Parameters
    ----------
    path
        Python file whose abstract syntax tree is inspected without importing
        or executing the module.

    Returns
    -------
    tuple[str, ...]
        Import and import-from module names in traversal order.
    """

    module = ast.parse(path.read_text(encoding="utf-8"))
    values: list[str] = []
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            values.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            values.append(node.module)
    return tuple(values)


def test__dependency_boundary__imports_only_exact_ingestion_leaf() -> None:
    """Allow the chunker module to import only ``PageProjectionResult``.

    Notes
    -----
    Exact module equality prevents a convenient broader Ingestion facade from
    silently becoming a production dependency.
    """

    ingestion_imports = tuple(
        value
        for value in _imports(CHUNKING_MODULE)
        if value.startswith("projectkoios.ingestion")
    )

    assert ingestion_imports == (EXACT_INGESTION_LEAF,)


def test__dependency_boundary__keeps_other_search_modules_independent() -> None:
    """Reject Ingestion imports outside the authorized chunking leaf.

    Notes
    -----
    Walking every Search-owned source file protects both present indexing code
    and later retrieval modules from accidental coupling.
    """

    violations: list[str] = []
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        if path == CHUNKING_MODULE:
            continue
        if any(
            value.startswith("projectkoios.ingestion")
            for value in _imports(path)
        ):
            violations.append(str(path.relative_to(REPOSITORY_ROOT)))

    assert not violations, "unexpected Ingestion imports:\n" + "\n".join(
        violations
    )


def test__dependency_boundary__keeps_search_facade_independent() -> None:
    """Prevent the package facade from eagerly loading the Ingestion leaf.

    Notes
    -----
    Python executes a package initializer before importing its children. A
    facade re-export would therefore make otherwise independent index imports
    require Ingestion at runtime.
    """

    facade_imports = _imports(SOURCE_ROOT / "search/__init__.py")

    assert "projectkoios.search.page_projection_chunking" not in facade_imports

from __future__ import annotations

import ast
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src/python/projectkoios"
CHUNKING_MODULE = SOURCE_ROOT / "search/page_projection_chunking.py"
EXACT_INGESTION_LEAF = "projectkoios.ingestion.page.projection.result"


def _imports(path: Path) -> tuple[str, ...]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    values: list[str] = []
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            values.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            values.append(node.module)
    return tuple(values)


def test__chunking_boundary__imports_only_exact_ingestion_leaf() -> None:
    ingestion_imports = tuple(
        value
        for value in _imports(CHUNKING_MODULE)
        if value.startswith("projectkoios.ingestion")
    )

    assert ingestion_imports == (EXACT_INGESTION_LEAF,)


def test__search_modules__keep_ingestion_outside_chunking_leaf() -> None:
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


def test__search_facade__does_not_load_chunking_dependency() -> None:
    facade_imports = _imports(SOURCE_ROOT / "search/__init__.py")

    assert "projectkoios.search.page_projection_chunking" not in facade_imports

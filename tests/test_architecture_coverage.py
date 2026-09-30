from __future__ import annotations

import ast
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src/python/projectkoios"
ARCHITECTURE_ROOT = REPOSITORY_ROOT / "docs/architecture/projectkoios"
DOCS_ROOT = REPOSITORY_ROOT / "docs"
TRIO = ("index.md", "schematic.md", "implementation.md")
MARKDOWN_LINK = re.compile(r"!?\[[^]]*\]\(([^)]+)\)")


def _python_files() -> tuple[Path, ...]:
    return tuple(sorted(SOURCE_ROOT.rglob("*.py")))


def _package_directories() -> tuple[Path, ...]:
    packages = {SOURCE_ROOT}
    for source_file in _python_files():
        current = source_file.parent
        while True:
            packages.add(current)
            if current == SOURCE_ROOT:
                break
            current = current.parent
    return tuple(sorted(packages))


def _owner_documentation(source_path: Path) -> Path:
    relative = source_path.relative_to(SOURCE_ROOT)
    if source_path.is_dir() or source_path.name == "__init__.py":
        relative = relative.parent if source_path.is_file() else relative
    else:
        relative = relative.with_suffix("")
    return ARCHITECTURE_ROOT.joinpath(*relative.parts)


def _source_owners() -> tuple[Path, ...]:
    modules = tuple(
        path for path in _python_files() if path.name != "__init__.py"
    )
    return tuple(sorted((*_package_directories(), *modules)))


def _public_defining_classes() -> tuple[tuple[Path, str], ...]:
    classes: list[tuple[Path, str]] = []
    for source_file in _python_files():
        module = ast.parse(source_file.read_text(encoding="utf-8"))
        classes.extend(
            (source_file, node.name)
            for node in module.body
            if isinstance(node, ast.ClassDef) and not node.name.startswith("_")
        )
    return tuple(classes)


def _format_paths(paths: set[Path]) -> str:
    return "\n".join(
        str(path.relative_to(REPOSITORY_ROOT)) for path in sorted(paths)
    )


def test__every_source_package_and_module_has_architecture_trio() -> None:
    missing: set[Path] = set()
    missing_mermaid: set[Path] = set()

    for source_owner in _source_owners():
        documentation = _owner_documentation(source_owner)
        for filename in TRIO:
            page = documentation / filename
            if not page.is_file():
                missing.add(page)
        for filename in ("schematic.md", "implementation.md"):
            page = documentation / filename
            if page.is_file() and "```mermaid" not in page.read_text(
                encoding="utf-8"
            ):
                missing_mermaid.add(page)

    assert not missing, "missing architecture pages:\n" + _format_paths(missing)
    assert not missing_mermaid, "missing Mermaid diagrams:\n" + _format_paths(
        missing_mermaid
    )


def test__public_defining_classes_have_exact_non_orphan_pages() -> None:
    owner_indexes = {
        _owner_documentation(owner) / "index.md" for owner in _source_owners()
    }
    expected_class_pages = {
        _owner_documentation(source_file) / class_name / "index.md"
        for source_file, class_name in _public_defining_classes()
    }
    actual_class_pages = (
        set(ARCHITECTURE_ROOT.rglob("index.md")) - owner_indexes
    )

    missing = expected_class_pages - actual_class_pages
    orphaned = actual_class_pages - expected_class_pages

    assert not missing, "missing class pages:\n" + _format_paths(missing)
    assert not orphaned, "orphan class pages:\n" + _format_paths(orphaned)


def test__documentation_local_links_resolve() -> None:
    broken: list[str] = []
    repository_root = REPOSITORY_ROOT.resolve()

    for document in sorted(DOCS_ROOT.rglob("*.md")):
        text = document.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            path_text = unquote(parsed.path)
            candidate = (
                REPOSITORY_ROOT / path_text.removeprefix("/")
                if path_text.startswith("/")
                else document.parent / path_text
            ).resolve()
            try:
                candidate.relative_to(repository_root)
            except ValueError:
                broken.append(f"{document}: {raw_target} escapes repository")
                continue
            if not candidate.exists():
                broken.append(f"{document}: {raw_target}")

    assert not broken, "broken local documentation links:\n" + "\n".join(broken)

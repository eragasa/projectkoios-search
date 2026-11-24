"""Adversarial tests for the local authority-bound mypy taxonomy gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.authority_bound_architecture_mypy_plugin import (
    authority_bound_architecture_violations,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _write_valid_repository(root: Path) -> Path:
    """Write the smallest valid authority-bound architecture fixture."""
    source = root / "src/python/projectkoios/search/authority_bound_evidence.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        """\
from dataclasses import dataclass
from projectkoios.base import DataObjectModel

@dataclass(frozen=True, slots=True, kw_only=True)
class ExampleContract(DataObjectModel):
    value: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.value, tuple):
            raise TypeError("value must be a tuple")
""",
        encoding="utf-8",
    )
    test = (
        root
        / "tests/projectkoios/search/test__AuthorityBoundEvidenceAdmission.py"
    )
    test.parent.mkdir(parents=True)
    test.write_text(
        """\
from projectkoios.search.authority_bound_evidence import ExampleContract


def test__example_contract__is_public() -> None:
    assert ExampleContract.__name__ == "ExampleContract"
""",
        encoding="utf-8",
    )
    return source


def _messages(root: Path) -> str:
    """Return fixture diagnostics as one assertion-friendly string."""
    return "\n".join(authority_bound_architecture_violations(root))


def test__authority_mypy_plugin__accepts_actual_tree() -> None:
    """Keep strict-mypy architecture evidence clean in the actual tree."""
    assert authority_bound_architecture_violations(REPOSITORY_ROOT) == ()


def test__authority_mypy_plugin__accepts_valid_fixture(
    tmp_path: Path,
) -> None:
    """Accept a frozen, slotted, validation-only public DataObject."""
    _write_valid_repository(tmp_path)
    assert authority_bound_architecture_violations(tmp_path) == ()


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    (
        ("class ExampleContract", "class _ExampleContract", "private classes"),
        (
            "class ExampleContract(DataObjectModel):",
            "class ExampleContract(DataObjectModel):\n    class Nested: pass",
            "nested classes",
        ),
        (
            "from dataclasses import dataclass",
            "from dataclasses import dataclass\nfrom elsewhere import _secret",
            "private import _secret is forbidden",
        ),
        (
            "@dataclass(frozen=True, slots=True, kw_only=True)",
            (
                "def public_helper() -> None: pass\n\n"
                "@dataclass(frozen=True, slots=True, kw_only=True)"
            ),
            "public helper functions",
        ),
        ("value: tuple[str, ...]", "value: list[str]", "must be immutable"),
        (
            "@dataclass(frozen=True, slots=True, kw_only=True)",
            "@dataclass(slots=True, kw_only=True)",
            "must be frozen and slotted",
        ),
        (
            "    def __post_init__(self) -> None:",
            (
                "    def execute(self) -> None: pass\n\n"
                "    def __post_init__(self) -> None:"
            ),
            "may only validate",
        ),
        (
            "    def __post_init__(self) -> None:",
            (
                "    @classmethod\n"
                "    def create(cls) -> None: pass\n\n"
                "    def __post_init__(self) -> None:"
            ),
            "classmethod/staticmethod",
        ),
    ),
)
def test__authority_mypy_plugin__rejects_forbidden_source_shapes(
    tmp_path: Path,
    old: str,
    new: str,
    expected: str,
) -> None:
    """Reject each forbidden class, import, function, or field shape."""
    source = _write_valid_repository(tmp_path)
    source.write_text(
        source.read_text(encoding="utf-8").replace(old, new),
        encoding="utf-8",
    )
    assert expected in _messages(tmp_path)


@pytest.mark.parametrize(
    ("source_text", "expected"),
    (
        (
            "class ExampleContract:\n    pass\n",
            "class is outside the allowed taxonomy",
        ),
        (
            """\
from dataclasses import dataclass
from projectkoios.base import DataObjectModel

@dataclass(frozen=True, slots=True)
class ExampleProvider(DataObjectModel):
    value: tuple[str, ...]
""",
            "multi-verb role name is forbidden",
        ),
        (
            """\
from projectkoios.base import DataObjectActionizer

class ExampleContract(DataObjectActionizer[object, object]):
    def action(self, request: object) -> object:
        return request
""",
            "action must consume one keyword-only request",
        ),
        (
            """\
from projectkoios.base import DataObjectActionizer

class ExampleContract(DataObjectActionizer[object, object]):
    def __init__(self) -> None:
        self.value = object()

    def action(self, *, request: object) -> object:
        return request
""",
            "Actionizer must expose only action",
        ),
        (
            """\
from projectkoios.base import DataObjectActionizer

class ExampleContract(DataObjectActionizer[object, object]):
    __slots__ = ("value",)

    def action(self, *, request: object) -> object:
        self.value = request
        return request
""",
            "Actionizer must be stateless with empty slots",
        ),
        (
            """\
from projectkoios.base import DataObjectActionizer

class ExampleContract(DataObjectActionizer[object, object]):
    __slots__ = ()

    def action(self, *, request: object) -> object:
        return request

    def load(self) -> object:
        return object()
""",
            "Actionizer must expose only action",
        ),
        (
            """\
from typing import Protocol

class ExampleContract(Protocol):
    def action(self, *, request: object) -> object: ...
    def load(self) -> object: ...
""",
            "action Protocol must expose only action",
        ),
        (
            """\
from enum import StrEnum

class ExampleContract(StrEnum):
    VALUE = "value"
    def load(self) -> str:
        return self.value
""",
            "enum/error classes cannot define operations",
        ),
        (
            """\
class ExampleError(ValueError):
    def __init__(self) -> None:
        super().__init__("error")
""",
            "enum/error classes cannot define operations",
        ),
        (
            """\
from typing import NamedTuple

_PrivateValues = NamedTuple("_PrivateValues", [("value", str)])
""",
            "private NamedTuple declarations are forbidden",
        ),
    ),
)
def test__authority_mypy_plugin__rejects_taxonomy_evasions(
    tmp_path: Path,
    source_text: str,
    expected: str,
) -> None:
    """Reject non-taxonomy classes, signatures, verbs, and named tuples."""
    source = _write_valid_repository(tmp_path)
    source.write_text(source_text, encoding="utf-8")
    assert expected in _messages(tmp_path)


@pytest.mark.parametrize(
    ("test_text", "expected"),
    (
        ("class _PrivateTest: pass\n", "private test classes"),
        (
            "def test__outer() -> None:\n    class Nested: pass\n",
            "nested test classes",
        ),
        (
            "from elsewhere import _secret\n",
            "tests cannot import private names",
        ),
        (
            "def public_helper() -> None: pass\n",
            "public helper is forbidden in tests",
        ),
    ),
)
def test__authority_mypy_plugin__rejects_forbidden_test_shapes(
    tmp_path: Path,
    test_text: str,
    expected: str,
) -> None:
    """Reject private, nested, imported, and public-helper test shapes."""
    _write_valid_repository(tmp_path)
    test = (
        tmp_path
        / "tests/projectkoios/search/test__AuthorityBoundEvidenceAdmission.py"
    )
    test.write_text(test_text, encoding="utf-8")
    assert expected in _messages(tmp_path)

"""Repository-local mypy gate for authority-bound authoring architecture."""

from __future__ import annotations

import ast
import hashlib
from collections.abc import Callable, Iterable
from pathlib import Path

from mypy.options import Options
from mypy.plugin import ClassDefContext, Plugin, ReportConfigContext

_AUTHORITY_SOURCE = Path(
    "src/python/projectkoios/search/authority_bound_evidence.py"
)
_AUTHORITY_TEST = Path(
    "tests/projectkoios/search/test__AuthorityBoundEvidenceAdmission.py"
)
_AUTHORITY_DOCS = Path(
    "docs/architecture/projectkoios/search/authority_bound_evidence"
)
_PASSIVE_BASES = frozenset(
    {"DataObjectModel", "DataObjectActionRequest", "DataObjectActionResult"}
)
_ACTIONIZER_BASE = "DataObjectActionizer"
_ENUM_BASES = frozenset({"Enum", "IntEnum", "StrEnum"})
_ERROR_BASES = frozenset(
    {"Exception", "RuntimeError", "TypeError", "ValueError"}
)
_FORBIDDEN_CLASS_TERMS = (
    "Provider",
    "Service",
    "Manager",
    "Repository",
    "Facade",
    "Helper",
)
_MUTABLE_ANNOTATIONS = frozenset({"dict", "list", "set", "Dict", "List", "Set"})


def _base_name(value: ast.expr) -> str:
    """Return the unqualified name of one base or decorator expression."""
    if isinstance(value, ast.Subscript):
        return _base_name(value.value)
    if isinstance(value, ast.Attribute):
        return value.attr
    if isinstance(value, ast.Name):
        return value.id
    return ast.unparse(value)


def _annotation_has_mutable_container(value: ast.expr | None) -> bool:
    """Return whether an annotation exposes a mutable container."""
    if value is None:
        return False
    return any(
        isinstance(node, (ast.Name, ast.Attribute))
        and (
            (node.id if isinstance(node, ast.Name) else node.attr)
            in _MUTABLE_ANNOTATIONS
        )
        for node in ast.walk(value)
    )


def _dataclass_is_frozen_and_slotted(node: ast.ClassDef) -> bool:
    """Return whether a class has exact immutable dataclass controls."""
    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        if _base_name(decorator.func) != "dataclass":
            continue
        keywords = {
            item.arg: item.value for item in decorator.keywords if item.arg
        }
        for name in ("frozen", "slots"):
            value = keywords.get(name)
            if not isinstance(value, ast.Constant) or value.value is not True:
                return False
        return True
    return False


def _class_methods(
    node: ast.ClassDef,
) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...]:
    """Return methods declared directly by one class."""
    return tuple(
        item
        for item in node.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def _actionizer_is_stateless(node: ast.ClassDef) -> bool:
    """Return whether an Actionizer declares empty slots and mutates no self."""
    empty_slots = False
    for statement in node.body:
        if not isinstance(statement, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "__slots__"
            for target in statement.targets
        ):
            continue
        empty_slots = isinstance(statement.value, ast.Tuple) and not (
            statement.value.elts
        )
    mutates_self = any(
        isinstance(item, ast.Attribute)
        and isinstance(item.ctx, (ast.Store, ast.Del))
        and isinstance(item.value, ast.Name)
        and item.value.id == "self"
        for item in ast.walk(node)
    )
    return empty_slots and not mutates_self


def _relative_label(path: Path, repository: Path) -> str:
    """Return a stable repository-relative diagnostic label."""
    try:
        return str(path.relative_to(repository))
    except ValueError:
        return str(path)


def _class_violations(
    *, node: ast.ClassDef, source: Path, repository: Path
) -> tuple[str, ...]:
    """Return nominal-taxonomy violations for one top-level source class."""
    label = f"{_relative_label(source, repository)}:{node.lineno}:{node.name}"
    violations: list[str] = []
    if node.name.startswith("_"):
        violations.append(f"{label}: private classes are forbidden")
    bases = {_base_name(item) for item in node.bases}
    methods = _class_methods(node)
    method_names = {item.name for item in methods}
    if any(
        _base_name(decorator) in {"classmethod", "staticmethod"}
        for method in methods
        for decorator in method.decorator_list
    ):
        violations.append(f"{label}: classmethod/staticmethod is forbidden")
    is_error = node.name.endswith("Error") and bool(bases & _ERROR_BASES)
    is_enum = bool(bases & _ENUM_BASES)
    is_actionizer = _ACTIONIZER_BASE in bases
    is_passive = bool(bases & _PASSIVE_BASES)
    is_protocol = "Protocol" in bases
    if is_actionizer:
        if not _actionizer_is_stateless(node):
            violations.append(
                f"{label}: Actionizer must be stateless with empty slots"
            )
        if method_names != {"action"}:
            violations.append(f"{label}: Actionizer must expose only action")
        action = next((item for item in methods if item.name == "action"), None)
        if action is not None:
            keyword_names = {item.arg for item in action.args.kwonlyargs}
            if (
                keyword_names != {"request"}
                or len(action.args.args) != 1
                or action.args.vararg is not None
                or action.args.kwarg is not None
            ):
                violations.append(
                    f"{label}: action must consume one keyword-only request"
                )
            if action.returns is None:
                violations.append(f"{label}: action must declare its Result")
    elif is_passive:
        if not _dataclass_is_frozen_and_slotted(node):
            violations.append(
                f"{label}: passive DataObject must be frozen and slotted"
            )
        if method_names - {"__post_init__"}:
            violations.append(
                f"{label}: passive DataObject may only validate in "
                "__post_init__"
            )
        for statement in node.body:
            if isinstance(
                statement, ast.AnnAssign
            ) and _annotation_has_mutable_container(statement.annotation):
                violations.append(
                    f"{label}: passive DataObject fields must be immutable"
                )
    elif is_protocol:
        if method_names != {"action"}:
            violations.append(
                f"{label}: action Protocol must expose only action"
            )
        action = next((item for item in methods if item.name == "action"), None)
        if action is not None:
            keyword_names = {item.arg for item in action.args.kwonlyargs}
            if (
                keyword_names != {"request"}
                or len(action.args.args) != 1
                or action.args.vararg is not None
                or action.args.kwarg is not None
                or action.returns is None
            ):
                violations.append(
                    f"{label}: Protocol action must declare Request and Result"
                )
    elif is_error or is_enum:
        if method_names:
            violations.append(
                f"{label}: enum/error classes cannot define operations"
            )
    else:
        violations.append(f"{label}: class is outside the allowed taxonomy")
    if not (is_error or is_enum) and any(
        term in node.name for term in _FORBIDDEN_CLASS_TERMS
    ):
        violations.append(f"{label}: multi-verb role name is forbidden")
    return tuple(violations)


def _source_violations(*, source: Path, repository: Path) -> tuple[str, ...]:
    """Return authority-bound source architecture violations."""
    label = _relative_label(source, repository)
    try:
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=label)
    except SyntaxError as error:
        return (f"{label}:{error.lineno or 1}: invalid Python syntax",)
    violations: list[str] = []
    top_level_classes = {
        id(item) for item in tree.body if isinstance(item, ast.ClassDef)
    }
    for item in ast.walk(tree):
        if isinstance(item, ast.ClassDef) and id(item) not in top_level_classes:
            violations.append(
                f"{label}:{item.lineno}:{item.name}: nested classes are "
                "forbidden"
            )
        if isinstance(item, ast.ImportFrom):
            for imported in item.names:
                if imported.name.startswith("_") and not (
                    imported.name.startswith("__")
                ):
                    violations.append(
                        f"{label}:{item.lineno}: private import "
                        f"{imported.name} is forbidden"
                    )
    for item in tree.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not (
            item.name.startswith("_")
        ):
            violations.append(
                f"{label}:{item.lineno}:{item.name}: public helper functions "
                "are forbidden"
            )
        assignment_name: str | None = None
        assignment_value: ast.expr | None = None
        if isinstance(item, ast.Assign) and len(item.targets) == 1:
            target = item.targets[0]
            if isinstance(target, ast.Name):
                assignment_name = target.id
                assignment_value = item.value
        elif isinstance(item, ast.AnnAssign) and isinstance(
            item.target, ast.Name
        ):
            assignment_name = item.target.id
            assignment_value = item.value
        if (
            assignment_name is not None
            and assignment_name.startswith("_")
            and isinstance(assignment_value, ast.Call)
            and _base_name(assignment_value.func) == "NamedTuple"
        ):
            violations.append(
                f"{label}:{item.lineno}:{assignment_name}: private "
                "NamedTuple declarations are forbidden"
            )
        if isinstance(item, ast.ClassDef):
            violations.extend(
                _class_violations(
                    node=item,
                    source=source,
                    repository=repository,
                )
            )
    return tuple(violations)


def _test_violations(*, test: Path, repository: Path) -> tuple[str, ...]:
    """Return forbidden test-module shapes for the authority slice."""
    label = _relative_label(test, repository)
    try:
        tree = ast.parse(test.read_text(encoding="utf-8"), filename=label)
    except SyntaxError as error:
        return (f"{label}:{error.lineno or 1}: invalid Python syntax",)
    violations: list[str] = []
    top_level_classes = {
        id(item) for item in tree.body if isinstance(item, ast.ClassDef)
    }
    for item in ast.walk(tree):
        if isinstance(item, ast.ClassDef):
            if item.name.startswith("_"):
                violations.append(
                    f"{label}:{item.lineno}:{item.name}: private test classes "
                    "are forbidden"
                )
            if id(item) not in top_level_classes:
                violations.append(
                    f"{label}:{item.lineno}:{item.name}: nested test classes "
                    "are forbidden"
                )
        if isinstance(item, ast.ImportFrom):
            for imported in item.names:
                if imported.name.startswith("_") and not (
                    imported.name.startswith("__")
                ):
                    violations.append(
                        f"{label}:{item.lineno}: tests cannot import private "
                        "names"
                    )
    for item in tree.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not (
            item.name.startswith("test_") or item.name.startswith("_")
        ):
            violations.append(
                f"{label}:{item.lineno}:{item.name}: public helper is "
                "forbidden in tests"
            )
    return tuple(violations)


def authority_bound_architecture_violations(
    repository: Path,
) -> tuple[str, ...]:
    """Return deterministic violations for the authority-bound slice."""
    violations: list[str] = []
    source = repository / _AUTHORITY_SOURCE
    test = repository / _AUTHORITY_TEST
    if not source.is_file():
        violations.append(f"{_AUTHORITY_SOURCE}: source is missing")
    else:
        violations.extend(
            _source_violations(source=source, repository=repository)
        )
    if not test.is_file():
        violations.append(f"{_AUTHORITY_TEST}: test is missing")
    else:
        violations.extend(_test_violations(test=test, repository=repository))
    return tuple(sorted(set(violations)))


def _architecture_digest(repository: Path) -> str:
    """Return a mypy cache key for authority architecture evidence."""
    digest = hashlib.sha256()
    roots: Iterable[Path] = (
        repository / _AUTHORITY_SOURCE,
        repository / _AUTHORITY_TEST,
        repository / _AUTHORITY_DOCS,
    )
    for root in roots:
        paths = (
            (root,)
            if root.is_file()
            else tuple(item for item in root.rglob("*") if item.is_file())
        )
        for path in sorted(paths):
            digest.update(str(path.relative_to(repository)).encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


class AuthorityBoundArchitecturePlugin(Plugin):
    """Make strict mypy the authoritative local architecture gate."""

    def __init__(self, options: Options) -> None:
        """Capture deterministic repository-local architecture evidence."""
        super().__init__(options)
        self._repository = Path(__file__).resolve().parent.parent
        self._violations = authority_bound_architecture_violations(
            self._repository
        )
        self._reported = False

    def get_customize_class_mro_hook(
        self,
        fullname: str,
    ) -> Callable[[ClassDefContext], None] | None:
        """Report local violations during authority semantic analysis."""
        if not fullname.startswith(
            "projectkoios.search.authority_bound_evidence."
        ):
            return None
        return self._report

    def _report(self, context: ClassDefContext) -> None:
        """Emit each repository-local diagnostic once per mypy run."""
        if self._reported:
            return
        self._reported = True
        for violation in self._violations:
            context.api.fail(
                f"authority-bound-taxonomy: {violation}",
                context.cls,
            )

    def report_config_data(self, context: ReportConfigContext) -> object:
        """Invalidate mypy caches when architecture evidence changes."""
        del context
        return {
            "authority_bound_architecture": _architecture_digest(
                self._repository
            )
        }


def plugin(version: str) -> type[AuthorityBoundArchitecturePlugin]:
    """Return the repository-local plugin type for mypy discovery."""
    del version
    return AuthorityBoundArchitecturePlugin

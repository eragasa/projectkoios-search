"""Operator-contract tests for development Mongo lexical verification."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import cast

import mongomock
import pytest
from pymongo.errors import ServerSelectionTimeoutError

_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "verify_mongodb_page_projection_lexical.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "verify_mongodb_page_projection_lexical",
    _SCRIPT,
)
assert _SPEC is not None and _SPEC.loader is not None
verification = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = verification
_SPEC.loader.exec_module(verification)
assert isinstance(verification, ModuleType)


def _descriptor(*, value: bytes) -> int:
    """Return a readable anonymous pipe containing one complete value."""

    reader, writer = os.pipe()
    try:
        os.write(writer, value)
    finally:
        os.close(writer)
    return reader


@contextmanager
def _connection_fd(*, value: bytes) -> Iterator[None]:
    """Install one pipe reader as FD 3 and restore the prior descriptor."""

    try:
        saved_descriptor = os.dup(3)
    except OSError:
        saved_descriptor = None
    reader = _descriptor(value=value)
    if reader != 3:
        os.dup2(reader, 3)
        os.close(reader)
    try:
        yield
    finally:
        try:
            os.close(3)
        except OSError:
            pass
        if saved_descriptor is not None:
            os.dup2(saved_descriptor, 3)
            os.close(saved_descriptor)


def _arguments() -> tuple[str, ...]:
    """Return the exact allowlisted nonsecret command arguments."""

    return (
        "--database-name",
        "projectkoios_search_development",
        "--storage-target-id",
        "projectkoios.search.mongodb.development",
        "--capability-id",
        (
            "mongodb-database-capability:sha256:"
            "d0286175d36e6de1ccba5c608cf2c6a78ca3f817e2d42f8e318b50f51c58a520"
        ),
        "--connection-uri-fd",
        "3",
    )


def _install_client(
    monkeypatch: pytest.MonkeyPatch,
) -> mongomock.MongoClient:
    """Install one reusable in-memory client constructor for command tests."""

    client = mongomock.MongoClient()

    def client_factory(
        connection_uri: str,
        **options: object,
    ) -> mongomock.MongoClient:
        assert connection_uri == "secret-connection-material"
        assert options == {
            "appname": "projectkoios-search-lexical-verification",
            "connectTimeoutMS": 5_000,
            "serverSelectionTimeoutMS": 5_000,
            "socketTimeoutMS": 15_000,
        }
        return client

    monkeypatch.setattr(verification, "MongoClient", client_factory)
    return client


def _run_success(
    *,
    capsys: pytest.CaptureFixture[str],
) -> dict[str, object]:
    """Run one command and return its sole decoded success line."""

    with _connection_fd(value=b"secret-connection-material"):
        assert verification.main(_arguments()) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    lines = captured.out.splitlines()
    assert len(lines) == 1
    assert len(captured.out.encode("utf-8")) <= 16_384
    assert "secret-connection-material" not in captured.out
    return cast(dict[str, object], json.loads(lines[0]))


def test__main__emits_one_frozen_safe_success_record(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Expose only allowlisted identities, measures, and deterministic hits."""

    _install_client(monkeypatch)

    record = _run_success(capsys=capsys)

    assert frozenset(record) == verification._SUCCESS_KEYS
    assert record["status"] == "verified"
    assert record["capability_id"] == (
        "mongodb-database-capability:sha256:"
        "d0286175d36e6de1ccba5c608cf2c6a78ca3f817e2d42f8e318b50f51c58a520"
    )
    assert record["database_name"] == "projectkoios_search_development"
    assert record["storage_target_id"] == (
        "projectkoios.search.mongodb.development"
    )
    assert record["corpus_id"] == (
        "page-projection-lexical-corpus:sha256:"
        "eb041c7c3e4ecc27496d1af8b932b9eea488cd0efe7fcc167e3427a2d03a7a86"
    )
    assert record["index_id"] == (
        "page-projection-lexical-index:sha256:"
        "45cd0a8d430610ef80f30795abe76f022caf3f5f94d7c1c8c02e092ac363e294"
    )
    assert record["generation_id"] == (
        "page-projection-lexical-generation:sha256:"
        "018c83217fb605bd6498386560fcd678e60a4a128f57343dea2dd1aa3f558fdf"
    )
    assert record["query_result_id"] == (
        "page-projection-lexical-search-result:sha256:"
        "3d2965fedad4e5f63ce2ab8276c8494b31cac4d92b8717756be4ef986bfd14ff"
    )
    assert record["chunk_count"] == 2
    assert record["posting_count"] == 4
    assert record["term_count"] == 4
    assert record["total_document_length"] == 4
    assert record["active_generation_id"] == record["generation_id"]
    assert record["hit_chunk_ids"] == [
        (
            "page-projection-chunk:sha256:"
            "2a0a234b8defe349adf812ab4d43836c4eafcb2157e895d809e4fba1fb4aa50a"
        ),
        (
            "page-projection-chunk:sha256:"
            "906984c89ad423e70aa3b697eb727d10eb489439a40ecf64dffb5a2edcdcfef8"
        ),
    ]


def test__main__is_idempotent_when_expected_generation_is_already_active(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Reverify content without changing an already-correct pointer revision."""

    client = _install_client(monkeypatch)
    first = _run_success(capsys=capsys)
    pointer_before = client["projectkoios_search_development"][
        "lexical_generations"
    ].find_one({"_id": "active"})
    assert pointer_before is not None

    second = _run_success(capsys=capsys)
    pointer_after = client["projectkoios_search_development"][
        "lexical_generations"
    ].find_one({"_id": "active"})

    assert second == first
    assert pointer_after == pointer_before


def test__main__fails_closed_on_existing_immutable_document_drift(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Reject altered generation content without traceback or secret output."""

    client = _install_client(monkeypatch)
    _run_success(capsys=capsys)
    client["projectkoios_search_development"][
        "page_projection_chunks"
    ].update_one({}, {"$set": {"text": "altered"}})

    with _connection_fd(value=b"secret-connection-material"):
        assert verification.main(_arguments()) == 4
    captured = capsys.readouterr()

    assert captured.err == ""
    assert captured.out == (
        '{"category":"verification","exit_code":4,"status":"failed"}\n'
    )
    assert "secret-connection-material" not in captured.out


@pytest.mark.parametrize(
    "value",
    (
        b"",
        b"line\nbreak",
        b"carriage\rreturn",
        b"control\x00value",
        b" leading-space",
        b"trailing-space ",
        b"\xff",
        b"x" * 8_193,
    ),
)
def test__main__rejects_invalid_secret_channel_values(
    value: bytes,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Read through EOF with a sentinel and reject unsafe URI bytes."""

    with _connection_fd(value=value):
        assert verification.main(_arguments()) == 2
        with pytest.raises(OSError):
            os.fstat(3)
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == (
        '{"category":"invocation","exit_code":2,"status":"failed"}\n'
    )


def test__main__rejects_non_allowlisted_invocation_without_reading_secret(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Reject other targets before opening any secret descriptor."""

    arguments = list(_arguments())
    arguments[1] = "production"

    assert verification.main(tuple(arguments)) == 2
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == (
        '{"category":"invocation","exit_code":2,"status":"failed"}\n'
    )


@pytest.mark.parametrize("descriptor", ("03", "4", "1024"))
def test__main__rejects_any_connection_descriptor_other_than_fd3(
    descriptor: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Reject non-FD3 values before attempting any descriptor read."""

    def unexpected_read(*, descriptor: int) -> str:
        del descriptor
        raise AssertionError("descriptor read must not occur")

    monkeypatch.setattr(
        verification,
        "_read_connection_uri",
        unexpected_read,
    )
    arguments = list(_arguments())
    arguments[-1] = descriptor

    assert verification.main(tuple(arguments)) == 2
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == (
        '{"category":"invocation","exit_code":2,"status":"failed"}\n'
    )


def test__module_command__uses_exact_one_line_failure_contract() -> None:
    """Run the Search-owned module without shell or import traceback."""

    repository = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        (
            sys.executable,
            "-m",
            "scripts.verify_mongodb_page_projection_lexical",
            "--database-name",
            "rejected",
            "--storage-target-id",
            "projectkoios.search.mongodb.development",
            "--capability-id",
            (
                "mongodb-database-capability:sha256:"
                "d0286175d36e6de1ccba5c608cf2c6a78ca3f817e2d42f8e318b50f51c58a520"
            ),
            "--connection-uri-fd",
            "3",
        ),
        cwd=repository,
        capture_output=True,
        check=False,
        shell=False,
        text=True,
        timeout=10,
    )

    assert result.returncode == 2
    assert result.stderr == ""
    assert result.stdout == (
        '{"category":"invocation","exit_code":2,"status":"failed"}\n'
    )


def test__main__redacts_driver_failures(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Map driver failures to one fixed record without exception details."""

    def failing_client(
        connection_uri: str,
        **options: object,
    ) -> None:
        del connection_uri, options
        raise ServerSelectionTimeoutError("sensitive endpoint detail")

    monkeypatch.setattr(
        verification,
        "MongoClient",
        cast(Callable[..., object], failing_client),
    )
    with _connection_fd(value=b"secret-connection-material"):
        assert verification.main(_arguments()) == 3
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == (
        '{"category":"connection","exit_code":3,"status":"failed"}\n'
    )
    assert "sensitive" not in captured.out

#!/usr/bin/env python3
"""Verify the Mongo page-projection lexical path on one allowlisted target.

This repository-only operator command accepts a secret connection URI through
an inherited anonymous-pipe file descriptor. It never accepts the URI on argv,
reads environment variables, prints exception details, or supports a production
target. Search owns all schema, index, staging, activation, and retrieval work;
the operator owns secret injection and the hard wall-clock timeout.
"""

from __future__ import annotations

import json
import os
import sys
import unicodedata
from dataclasses import dataclass
from typing import Final

from projectkoios.indexing.mongodb_page_projection_lexical import (
    MongoPageProjectionLexicalError,
    MongoPageProjectionLexicalProjector,
    MongoPageProjectionLexicalRetriever,
)
from projectkoios.search.page_projection_lexical import (
    PageProjectionLexicalChunk,
    PageProjectionLexicalSearchRequest,
)
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from tests.projectkoios.search.page_projection_chunking.fixture.chunking import (  # noqa: E501
    derive_chunking_result,
)

_ALLOWED_DATABASE_NAME: Final[str] = "projectkoios_search_development"
_ALLOWED_STORAGE_TARGET_ID: Final[str] = (
    "projectkoios.search.mongodb.development"
)
_ALLOWED_CAPABILITY_ID: Final[str] = (
    "mongodb-database-capability:sha256:"
    "d0286175d36e6de1ccba5c608cf2c6a78ca3f817e2d42f8e318b50f51c58a520"
)
_MAXIMUM_SECRET_BYTES: Final[int] = 8_192
_MAXIMUM_OUTPUT_BYTES: Final[int] = 16_384
_CONNECTION_TIMEOUT_MILLISECONDS: Final[int] = 5_000
_SOCKET_TIMEOUT_MILLISECONDS: Final[int] = 15_000
_CONNECTION_URI_DESCRIPTOR: Final[int] = 3
_EXPECTED_ARGUMENT_NAMES: Final[tuple[str, ...]] = (
    "--database-name",
    "--storage-target-id",
    "--capability-id",
    "--connection-uri-fd",
)
_SUCCESS_KEYS: Final[frozenset[str]] = frozenset(
    {
        "active_generation_id",
        "capability_id",
        "chunk_count",
        "corpus_id",
        "database_name",
        "generation_id",
        "hit_chunk_ids",
        "index_id",
        "posting_count",
        "query_result_id",
        "status",
        "storage_target_id",
        "term_count",
        "total_document_length",
    }
)
_FAILURE_KEYS: Final[frozenset[str]] = frozenset(
    {"category", "exit_code", "status"}
)


@dataclass(frozen=True, slots=True, kw_only=True)
class _Arguments:
    """Retain exact nonsecret allowlisted invocation values."""

    database_name: str
    storage_target_id: str
    capability_id: str
    connection_uri_fd: int


class _InvocationError(ValueError):
    """Report a redacted invocation or secret-channel rejection."""


class _VerificationError(RuntimeError):
    """Report a redacted fixture or result mismatch."""


def _parse_arguments(*, argv: tuple[str, ...]) -> _Arguments:
    """Parse the one closed, positional-pair operator command shape.

    Parameters
    ----------
    argv
        Arguments excluding the executable/module name.

    Returns
    -------
    _Arguments
        Exact validated nonsecret values and inherited descriptor number.

    Raises
    ------
    _InvocationError
        If names, ordering, values, or descriptor syntax differ.
    """

    if len(argv) != len(_EXPECTED_ARGUMENT_NAMES) * 2:
        raise _InvocationError("argument count rejected")
    observed_names = tuple(argv[offset] for offset in range(0, len(argv), 2))
    if observed_names != _EXPECTED_ARGUMENT_NAMES:
        raise _InvocationError("argument names rejected")
    database_name, storage_target_id, capability_id, descriptor_text = (
        argv[offset] for offset in range(1, len(argv), 2)
    )
    if database_name != _ALLOWED_DATABASE_NAME:
        raise _InvocationError("database target rejected")
    if storage_target_id != _ALLOWED_STORAGE_TARGET_ID:
        raise _InvocationError("storage target rejected")
    if capability_id != _ALLOWED_CAPABILITY_ID:
        raise _InvocationError("capability identity rejected")
    if descriptor_text != str(_CONNECTION_URI_DESCRIPTOR):
        raise _InvocationError("descriptor identity rejected")
    descriptor = _CONNECTION_URI_DESCRIPTOR
    return _Arguments(
        database_name=database_name,
        storage_target_id=storage_target_id,
        capability_id=capability_id,
        connection_uri_fd=descriptor,
    )


def _read_connection_uri(*, descriptor: int) -> str:
    """Read and close one bounded secret pipe through EOF without truncation.

    Parameters
    ----------
    descriptor
        Inherited readable anonymous-pipe file descriptor.

    Returns
    -------
    str
        Exact nonblank URI retained only in process memory.

    Raises
    ------
    _InvocationError
        If I/O, size, encoding, whitespace, or control validation fails.
    """

    value = bytearray()
    try:
        while len(value) <= _MAXIMUM_SECRET_BYTES:
            chunk = os.read(
                descriptor,
                _MAXIMUM_SECRET_BYTES + 1 - len(value),
            )
            if not chunk:
                break
            value.extend(chunk)
    except OSError as error:
        raise _InvocationError("secret descriptor read rejected") from error
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass
    if not value or len(value) > _MAXIMUM_SECRET_BYTES:
        raise _InvocationError("secret size rejected")
    try:
        connection_uri = bytes(value).decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise _InvocationError("secret encoding rejected") from error
    finally:
        value.clear()
    if (
        not connection_uri
        or connection_uri != connection_uri.strip()
        or any(
            character in {"\r", "\n"}
            or unicodedata.category(character).startswith("C")
            for character in connection_uri
        )
    ):
        raise _InvocationError("secret characters rejected")
    return connection_uri


def _safe_chunks() -> tuple[PageProjectionLexicalChunk, ...]:
    """Return the exact two chunks from the frozen sanitized fixture.

    Returns
    -------
    tuple[PageProjectionLexicalChunk, ...]
        Exact production chunk outputs through the structural adapter contract.
    """

    chunks = tuple(derive_chunking_result().chunks)
    if len(chunks) != 2 or not all(
        isinstance(value, PageProjectionLexicalChunk) for value in chunks
    ):
        raise _VerificationError("fixture projection rejected")
    return chunks


def _verify(*, arguments: _Arguments, connection_uri: str) -> dict[str, object]:
    """Run the complete bounded development-only Mongo verification.

    Parameters
    ----------
    arguments
        Exact nonsecret allowlisted invocation values.
    connection_uri
        In-memory secret connection value read from the inherited pipe.

    Returns
    -------
    dict[str, object]
        Safe success record conforming to the frozen key allowlist.
    """

    client: MongoClient[dict[str, object]] = MongoClient(
        connection_uri,
        appname="projectkoios-search-lexical-verification",
        connectTimeoutMS=_CONNECTION_TIMEOUT_MILLISECONDS,
        serverSelectionTimeoutMS=_CONNECTION_TIMEOUT_MILLISECONDS,
        socketTimeoutMS=_SOCKET_TIMEOUT_MILLISECONDS,
    )
    try:
        database = client.get_database(arguments.database_name)
        ping = database.command("ping")
        if ping.get("ok") != 1.0:
            raise _VerificationError("database capability rejected")
        chunks = _safe_chunks()
        projector = MongoPageProjectionLexicalProjector(
            database=database,
            storage_target_id=arguments.storage_target_id,
        )
        generation = projector.stage(chunks=chunks)
        replayed = projector.stage(chunks=tuple(reversed(chunks)))
        if generation != replayed:
            raise _VerificationError("permutation replay differs")
        if (
            generation.chunk_count != 2
            or generation.posting_count != 4
            or generation.term_count != 4
            or generation.total_document_length != 4
        ):
            raise _VerificationError("generation measures differ")
        active = projector.active_generation()
        if active is None:
            activated = projector.activate(
                generation=generation,
                expected_active_generation_id=None,
            )
        elif active.generation_id == generation.generation_id:
            # ``stage`` has just fully reverified immutable content; avoiding a
            # redundant pointer update makes repeated verification idempotent.
            activated = active
        else:
            activated = projector.activate(
                generation=generation,
                expected_active_generation_id=active.generation_id,
            )
        if activated != generation:
            raise _VerificationError("active generation differs")
        retriever = MongoPageProjectionLexicalRetriever(
            database=database,
            storage_target_id=arguments.storage_target_id,
        )
        result = retriever.search(
            request=PageProjectionLexicalSearchRequest(
                query="canonical title",
                limit=2,
                maximum_candidate_postings=8,
            )
        )
        expected_chunk_ids = tuple(sorted(value.chunk_id for value in chunks))
        observed_chunk_ids = tuple(value.chunk_id for value in result.hits)
        if (
            result.generation_id != generation.generation_id
            or result.normalized_query_terms != ("canonical", "title")
            or observed_chunk_ids != expected_chunk_ids
            or tuple(value.rank for value in result.hits) != (1, 2)
        ):
            raise _VerificationError("retrieval evidence differs")
        success: dict[str, object] = {
            "active_generation_id": activated.generation_id,
            "capability_id": arguments.capability_id,
            "chunk_count": generation.chunk_count,
            "corpus_id": generation.corpus_id,
            "database_name": arguments.database_name,
            "generation_id": generation.generation_id,
            "hit_chunk_ids": observed_chunk_ids,
            "index_id": generation.index_id,
            "posting_count": generation.posting_count,
            "query_result_id": result.result_id,
            "status": "verified",
            "storage_target_id": arguments.storage_target_id,
            "term_count": generation.term_count,
            "total_document_length": generation.total_document_length,
        }
        if frozenset(success) != _SUCCESS_KEYS:
            raise _VerificationError("success output schema differs")
        return success
    finally:
        client.close()


def _has_driver_cause(*, error: BaseException) -> bool:
    """Return whether an exception chain contains a Mongo driver failure.

    Parameters
    ----------
    error
        Caught adapter or unexpected error.

    Returns
    -------
    bool
        ``True`` only when a ``PyMongoError`` appears in the cause chain.
    """

    observed: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in observed:
        observed.add(id(current))
        if isinstance(current, PyMongoError):
            return True
        current = current.__cause__ or current.__context__
    return False


def _emit(*, record: dict[str, object], expected_keys: frozenset[str]) -> None:
    """Write exactly one bounded compact JSON line to stdout.

    Parameters
    ----------
    record
        Safe record containing no connection material or exception text.
    expected_keys
        Frozen exact key allowlist for this record variant.

    Raises
    ------
    RuntimeError
        If keys or the encoded line violate the output contract.
    """

    if frozenset(record) != expected_keys:
        raise RuntimeError("output schema rejected")
    encoded = json.dumps(
        record,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8", errors="strict")
    if len(encoded) + 1 > _MAXIMUM_OUTPUT_BYTES:
        raise RuntimeError("output size rejected")
    sys.stdout.buffer.write(encoded + b"\n")
    sys.stdout.buffer.flush()


def _failure(*, exit_code: int, category: str) -> int:
    """Emit one fixed redacted failure record and return its exit code."""

    _emit(
        record={
            "category": category,
            "exit_code": exit_code,
            "status": "failed",
        },
        expected_keys=_FAILURE_KEYS,
    )
    return exit_code


def main(argv: tuple[str, ...] | None = None) -> int:
    """Execute the development-only verifier with fully redacted failures.

    Parameters
    ----------
    argv
        Optional arguments excluding executable name; defaults to ``sys.argv``.

    Returns
    -------
    int
        ``0`` for verified, ``2`` for invocation rejection, ``3`` for driver
        capability failure, or ``4`` for fixture/adapter verification failure.
    """

    try:
        arguments = _parse_arguments(
            argv=tuple(sys.argv[1:]) if argv is None else argv
        )
        connection_uri = _read_connection_uri(
            descriptor=arguments.connection_uri_fd
        )
    except _InvocationError:
        return _failure(exit_code=2, category="invocation")
    try:
        success = _verify(
            arguments=arguments,
            connection_uri=connection_uri,
        )
    except PyMongoError:
        return _failure(exit_code=3, category="connection")
    except MongoPageProjectionLexicalError as error:
        if _has_driver_cause(error=error):
            return _failure(exit_code=3, category="connection")
        return _failure(exit_code=4, category="verification")
    except Exception:
        return _failure(exit_code=4, category="verification")
    finally:
        connection_uri = ""
    _emit(record=success, expected_keys=_SUCCESS_KEYS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

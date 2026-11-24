#!/usr/bin/env python3
"""Read-only preflight for one current-schema lexical corpus-union admission."""

from __future__ import annotations

import sys

from projectkoios.indexing.mongodb_page_projection_lexical import (
    MongoPageProjectionLexicalError,
)
from pymongo.errors import PyMongoError

from scripts.page_projection_lexical_admission import (
    AdmissionInventoryError,
    AdmissionInvocationError,
    AdmissionOutputError,
    AdmissionOwnerLoadError,
    AdmissionStateError,
    emit_failure,
    emit_success,
    has_driver_cause,
    parse_arguments,
    read_connection_uri,
    run_preflight,
)

_PHASE = "read-only-preflight"


def main(argv: tuple[str, ...] | None = None) -> int:
    """Run one bounded read-only preflight with redacted failures."""

    try:
        arguments = parse_arguments(
            argv=tuple(sys.argv[1:]) if argv is None else argv,
            admission=False,
        )
        connection_uri = read_connection_uri()
    except AdmissionInvocationError:
        return emit_failure(exit_code=2, category="invocation", phase=_PHASE)
    try:
        record = run_preflight(
            arguments=arguments,
            connection_uri=connection_uri,
        )
    except AdmissionOwnerLoadError:
        return emit_failure(exit_code=3, category="owner-load", phase=_PHASE)
    except AdmissionInventoryError:
        return emit_failure(exit_code=4, category="inventory", phase=_PHASE)
    except PyMongoError:
        return emit_failure(exit_code=5, category="connection", phase=_PHASE)
    except MongoPageProjectionLexicalError as error:
        return emit_failure(
            exit_code=5 if has_driver_cause(error=error) else 6,
            category=(
                "connection" if has_driver_cause(error=error) else "state"
            ),
            phase=_PHASE,
        )
    except AdmissionStateError:
        return emit_failure(exit_code=6, category="state", phase=_PHASE)
    except Exception:
        return emit_failure(exit_code=9, category="unexpected", phase=_PHASE)
    finally:
        connection_uri = ""
    try:
        emit_success(record=record, phase=_PHASE)
    except AdmissionOutputError:
        return emit_failure(exit_code=10, category="output", phase=_PHASE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

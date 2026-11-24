"""Bounded command-line inspection of a page-search index."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from projectkoios.search.page_search import PageSearchIndex


def main(argv: Sequence[str] | None = None) -> int:
    """Inspect status or run a bounded query without opening SQLite directly."""
    parser = argparse.ArgumentParser(prog="koios-page-search-index")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status")
    status.add_argument("--database", type=Path, required=True)

    query = subparsers.add_parser("query")
    query.add_argument("--database", type=Path, required=True)
    query.add_argument("--query", required=True)
    query.add_argument("--limit", type=int, default=10)
    query.add_argument("--offset", type=int, default=0)

    arguments = parser.parse_args(argv)
    index = PageSearchIndex(arguments.database)
    result = (
        index.status()
        if arguments.command == "status"
        else index.search(
            arguments.query,
            limit=arguments.limit,
            offset=arguments.offset,
        )
    )
    print(json.dumps(_to_json(result), ensure_ascii=False, sort_keys=True))
    return 0


def _to_json(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {
            key: _to_json(getattr(value, key))
            for key in value.__dataclass_fields__
        }
    if isinstance(value, tuple):
        return [_to_json(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())

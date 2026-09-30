# `projectkoios.search.service`

This module owns two thin dependency-injected services. Each delegates to its
corresponding protocol without adding validation, ranking, conversion, or
fallback behavior.

## Public classes

- [`RoleScopedSearchService`](RoleScopedSearchService/index.md)
- [`SearchService`](SearchService/index.md)

## Contents

- [`schematic.md`](schematic.md) — service-to-protocol relationships.
- [`implementation.md`](implementation.md) — pass-through call paths.

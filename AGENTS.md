# projectkoios-search

This repo owns full-text and semantic search infrastructure.

Repository routing is documented in `projectkoios-bootstrap/maps/repositories.md`.
This repo does not own cross-repo routing or product architecture policy.

## Implementation architecture documentation

Search implementation architecture lives under `docs/architecture/` and
mirrors the Python ownership path:

```text
docs/architecture/projectkoios/search/<module>/<ClassName>/index.md
```

Every source package, subpackage, and module is required to have a matching
directory containing `index.md`, `schematic.md`, and `implementation.md`.
Every public class is required to have an exact-name directory under its
defining module containing `index.md`. Package and module schematic and
implementation pages include appropriate Mermaid diagrams. Existing legacy
modules are pending an explicit migration into this structure; that migration
debt does not weaken the durable convention. Do not maintain a duplicate flat
architecture document or a tombstone for a replaced prototype page.

Project Koios living architecture may be cited for product boundaries only.
This repository owns its implementation architecture, class inventory,
algorithms, parameters, and source-to-documentation coverage.

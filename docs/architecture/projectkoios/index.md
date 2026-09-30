# `projectkoios` namespace implementation architecture

This directory describes the Python namespace portions implemented by
`projectkoios-search`. It is implementation architecture owned by this
repository, not a copy of cross-repository product architecture.

The Project Koios
[evidence-grounded long-form authoring boundary](https://github.com/eragasa/projectkoios/blob/d8a4867d581af81b76d10685b295df2abd1d632e/docs/architecture/v0/index.md#evidence-grounded-long-form-authoring)
defines the product boundary. The Search repository owns the classes,
algorithms, bounds, and validation described below.

## Contents

- [`indexing`](indexing/index.md) — in-memory index implementations and facade.
- [`search`](search/index.md) — search models, protocols, services, and retrieval families.
- [`schematic.md`](schematic.md) — namespace relationships.
- [`implementation.md`](implementation.md) — namespace implementation rules.

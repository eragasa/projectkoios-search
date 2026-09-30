# `EvidencePassage`

`EvidencePassage` is a frozen record containing passage and source identities,
a source SHA-256 value, optional citation key, BibTeX-presence flag, one-based
physical page, optional printed-page label, and evidence text.

This prototype record performs no field validation or identity derivation; its
producer is responsible for supplying coherent values.

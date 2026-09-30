# `LiteratureEvidenceBundleService`

The service receives a `PurposeScopedEvidenceIndex` and builds bounded evidence
for `LiteratureClaimQuery`. It accepts only literature-review claims and issues
one reference-only request per query in claim order.

Selection removes repeated passage IDs, limits repeated sources, preserves index
result order across query order, stops at the total limit, and assigns
contiguous `E1`-style labels. Default bounds are six results per query, ten in
the bundle, and two per source; validated maxima are 12, 12, and 2.

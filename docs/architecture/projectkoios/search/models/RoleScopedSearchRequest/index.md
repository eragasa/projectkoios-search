# `RoleScopedSearchRequest`

`RoleScopedSearchRequest` is a frozen record containing a nonblank query,
explicit `RetrievalPurpose`, unique excluded record IDs, and positive result
limit. It does not expose a caller-supplied corpus-role allowlist; roles come
from the index's admission policy.

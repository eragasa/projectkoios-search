# `UnsupportedRetrievalPurposeError`

**Base:** `ValueError`.

`RoleAdmissionPolicy.admitted_roles_for` raises this error when no admission is
configured for a requested `RetrievalPurpose`. The distinct type allows callers
to recognize a fail-closed policy rejection without treating it as an empty
search result.

# `LiteratureClaimQuery`

`LiteratureClaimQuery` is a frozen record containing a nonblank claim ID, 1–8
unique query strings, and a purpose defaulting to
`RetrievalPurpose.LITERATURE_REVIEW`. Each query must be nonblank under
`strip()` and no longer than 2,000 characters.

The record permits an explicit alternate purpose, but the bundle service rejects
anything other than literature review.

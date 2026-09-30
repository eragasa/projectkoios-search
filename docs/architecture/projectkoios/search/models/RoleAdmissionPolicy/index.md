# `RoleAdmissionPolicy`

`RoleAdmissionPolicy` is a frozen, nonempty tuple of `PurposeAdmission` records.
Construction requires explicit records and unique purposes.
`admitted_roles_for(purpose)` returns the matching role tuple or raises
`UnsupportedRetrievalPurposeError`; it does not substitute another purpose.

# `PurposeAdmission`

`PurposeAdmission` is a frozen pairing of one explicit `RetrievalPurpose` with
a nonempty tuple of admitted `CorpusRole` values. Construction rejects duplicate
roles and values of the wrong runtime enum type.

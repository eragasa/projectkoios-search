# AuthorityBoundEvidenceAdmissionRequest

`AuthorityBoundEvidenceAdmissionRequest` binds exact Search chunking, public
Ingestion enrichment, a References Search authority projection, and the result
ID that the caller expects to be current. Construction replays A and B, validates
C, checks projection consistency and bounds, and rejects a stale C checkpoint.

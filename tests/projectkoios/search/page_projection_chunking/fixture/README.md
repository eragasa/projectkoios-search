# Page-projection fixture reconstruction support

These test-local builders reconstruct the real typed synthetic
`PageProjectionResult` observed by the copied Ingestion fixture. The reading,
visual, and mixed-page builders are adapted from the corresponding Ingestion test fixtures at
implementation baseline `42d6a1499c2487359c4210de96d7cb3023013f5b`;
`result.py` assembles the exact source-result, managed-artifact verification,
page-projection request, and pure action used for the cross-repository
observation. The small observation projector follows fixture schema `1` frozen
by Ingestion fixture-producing commit
`b643f111436b40264e8c2343b1b20e8875f637d7`; producer lineage README commit
`cf58ab141311c5f2a9e6213c3b83a193af388ca5` names that immutable producer
without changing the fixture blob.

They are not production DTOs, codecs, alternate page projectors, compatibility
surfaces, or application composition. Production Search imports only
`projectkoios.ingestion.page.projection.result.PageProjectionResult` and never
imports Ingestion test code.

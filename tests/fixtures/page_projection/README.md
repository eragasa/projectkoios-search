# Page-projection chunking fixtures

`current-schema-v1.json` is copied byte-for-byte from the Ingestion-owned
sanitized observation of one real typed synthetic `PageProjectionResult`.
It is test evidence, not a production wire format, codec, compatibility promise,
publication record, or replacement for the typed Python contract.

## Ingestion-owned input

- Source repository: `projectkoios-ingestion`
- Source path: `tests/fixtures/page_projection/current-schema-v1.json`
- Page-projection implementation baseline:
  `42d6a1499c2487359c4210de96d7cb3023013f5b`
- Fixture-producing commit:
  `b643f111436b40264e8c2343b1b20e8875f637d7`
- Producer lineage README commit:
  `cf58ab141311c5f2a9e6213c3b83a193af388ca5`
- Fixture kind: `projectkoios.ingestion.page-projection-observation`
- Fixture schema: `1`
- Byte length: `2554`
- SHA-256: `9e725777ebb87f5a9fc69ebbcb64d69c98aabd205a3e92c95840c13fac538c8f`
- Git blob OID: `16ccea4aef4154531d2963f9cca7c41280ee19c7`

The copied bytes are compact sorted-key UTF-8 JSON with no terminal newline.
Search tests independently reconstruct the real typed synthetic result, compare
its sanitized observation with these exact bytes, and then pass the typed result
directly to the Search-owned chunker. The fixture-producing commit above owns
the immutable bytes; the separate producer lineage README commit names that
commit without changing the fixture blob.

## Search-owned expectation

`current-schema-v1.expected-chunks.json` records the exact deterministic output
of chunking that typed result under chunking contract and policy version `1.0`.
It contains two chunks: one exact paragraph and one exact figure caption. The
source fixture's canonical table and equation blocks remain absent because the
Ingestion projection excluded them before the Search boundary.

- Fixture kind: `projectkoios.search.page-projection-chunking-observation`
- Fixture schema: `1`
- Byte length: `4993`
- SHA-256: `8b11964d2c5f870eb30f642c45094ce41c1b92d42055c51707b345391630e7b8`
- Git blob OID: `4fc157fb52e9f72ad0d5a5a9e932e27849aa326c`

Neither fixture grants indexing, retrieval admission, publication, model,
workflow, application-composition, proofreading, citation-acceptance, or
scientific authority.

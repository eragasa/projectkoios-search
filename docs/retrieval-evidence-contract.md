# Source-linked retrieval evidence contract

## Status

Proposed under
[`SEARCH-EVIDENCE-01`](https://github.com/eragasa/projectkoios-search/issues/1).
This planning contract does not authorize implementation, corpus publication,
embedding generation, or answer generation.

## Purpose

Search must return bounded, source-resolvable evidence rather than display text
with an unexplained score. This contract defines the information shared by
future lexical, semantic, equation, fusion, API, and generation layers while
keeping their implementations independent.

The current `TextChunk` and `ChunkSearchResult` types are observed prototypes.
They are not the accepted evidence contract.

## Source boundary

Retrievable evidence originates from immutable extraction-derived artifacts.
Eligible evidence may include:

- audited transcript text linked to exact raw blocks and source spans;
- retained structured table or figure evidence;
- equation native text and separately identified symbolic proposals; and
- source metadata needed to resolve document and page identity.

The source corpus excludes:

- Markdown reference notes;
- generated summaries and relevance assessments;
- model answers and citation prose;
- manuscript drafts; and
- retrieval or evaluation output presented as source evidence.

Generated artifacts may be retained in a separate provenance graph. They never
silently become retrievable source evidence.

## Contract layers

The contract separates:

1. source evidence references;
2. retrievable evidence units;
3. lane-specific retrieval observations;
4. deterministic fusion observations; and
5. bounded evidence bundles.

A layer may refer to an earlier layer by immutable identity. It may not copy
and alter source content without a separately identified derivation.

## Source evidence reference

A source reference contains enough information to resolve immutable evidence
without relying on a display locator. It binds at least:

- corpus and corpus-version identity;
- bibliographic candidate or accepted-reference identity;
- source-asset and extraction identity;
- derivation-artifact identity;
- document and physical-page identity;
- printed-page label when available;
- exact block, span, region, equation, table, or figure identities;
- source-content digest;
- candidate or accepted status;
- warnings and uncertainty links; and
- source contract version.

A printed page number, citation string, filename, or UI label is not sufficient
as the sole identity.

Missing, contradictory, or unresolvable required identities fail closed.

## Evidence units

Every evidence unit has:

- deterministic unit identity;
- one evidence kind;
- ordered source references;
- exact indexed representation;
- transformation identity;
- unit-construction configuration and version;
- token or character counts needed to enforce bounds;
- warnings and uncertainty;
- candidate or accepted status; and
- stable content digest.

Text, equation, table, and figure evidence use typed representations. They are
not forced into a single lossy text field merely to share a ranking interface.
A lane may derive a documented search representation while retaining the typed
source record.

A unit spanning multiple blocks records every ordered source reference and the
rule permitting the join. Units may not cross document, page, section, or
structural boundaries unless a versioned construction policy explicitly allows
and tests that case.

## Deterministic identity

Evidence-unit identity binds source identities, ordered spans,
representation, construction policy, and contract version. Display order,
retrieval rank, mutable timestamps, and process-local values do not affect
identity.

Corpus and index identities bind the complete ordered manifest of admitted
units plus all preprocessing, tokenization, model, and ranking configuration
required to reproduce the index.

A changed source, candidate status, warning policy, chunking decision, or
processor version produces a new identity. Existing immutable indexes are not
silently updated in place.

## Lane observations

A retrieval lane returns observations rather than generic hits. Each
observation records:

- query identity and normalized lane query;
- lane kind and implementation version;
- corpus and index identity;
- evidence-unit identity;
- raw lane score with score semantics;
- one-based rank;
- deterministic tie-break key;
- parameters and filters;
- warnings; and
- observation identity.

A score is not represented as a probability unless the lane contract and
calibration evidence justify that interpretation.

Lexical, semantic, and equation observations remain distinguishable. Fusion
must not overwrite their native scores or ranks.

## Fusion observations

A fused result records:

- fusion method and version;
- participating and absent lanes;
- input observation identities and ranks;
- fusion parameters;
- deterministic contribution calculation;
- final score and rank;
- tie-break evidence; and
- fused-observation identity.

The initial proposed baseline is reciprocal-rank fusion. Its adoption and
parameters remain separate decisions. Fusion is not allowed to treat missing
lane evidence as a negative scientific judgment.

## Evidence bundle

An `EvidenceBundle` is the bounded output of search. It contains at least:

- bundle and query identity;
- original query and explicitly recorded normalization;
- corpus and index identities;
- applied source-status and rights filters;
- ordered selected evidence units;
- linked lane and fusion observations;
- source-resolution information;
- warnings and uncertainty;
- truncation and omitted-result counts;
- requested and applied bounds;
- outcome kind; and
- contract version.

Bounds cover query size, candidate count, selected evidence count, source-span
count, per-unit size, aggregate bundle size, nesting depth, and serialized
size. Exact defaults belong to a versioned configuration and must be tested at
and beyond each boundary.

Bundle identity binds its evidence and selection process. A display client may
reformat a bundle but cannot replace its source identities or ranking evidence.

## Outcome semantics

A bounded search outcome is conceptually one of:

- evidence available;
- insufficient evidence;
- invalid request;
- unsupported query or evidence kind; or
- infrastructure failure.

`INSUFFICIENT_EVIDENCE` means the admitted corpus and executed retrieval policy
did not provide evidence satisfying the bounded request. It is not a claim of
irrelevance, absence from the underlying source, falsity, or scientific
invalidity.

Infrastructure failure, missing indexes, rejected bounds, and unsupported
queries must not be converted into `INSUFFICIENT_EVIDENCE`.

## Candidate and accepted status

Candidate and accepted references remain distinguishable in source references,
evidence units, filters, and bundles. A query may explicitly include candidate
evidence, but the result must retain its candidate status.

Search, ranking, retrieval frequency, or model preference cannot promote a
candidate to the canonical bibliography.

## Equation evidence

Equation evidence keeps separate:

- exact native PDF text;
- rendered-region identity and digest;
- proposed LaTeX;
- proposed MathML;
- assembly and enrichment evidence;
- quality or admission status; and
- human or scientific interpretation.

A lane may index one or more explicit representations. It may not present a
model proposal as native source text or an interpretation as a verified
formula.

## Citation resolution

A downstream citation validator may establish that:

- an evidence-unit identity exists in the bundle;
- its source references resolve;
- a locator belongs to the referenced source; and
- an exact quoted string occurs in retained evidence.

It does not establish entailment, scientific correctness, canonical acceptance,
or publication suitability.

## Serialization boundary

Internal records use immutable dataclasses or ordinary domain classes. External
serialization uses a separately versioned boundary schema that:

- rejects unknown fields;
- validates all bounds before constructing internal records;
- uses explicit enum values and schema versions;
- avoids machine-specific paths;
- serializes deterministic ordered collections; and
- retains enough identity to resolve source evidence.

Search core contracts import no FastAPI, agent, UI, Obsidian, Petri-net,
embedding-runtime, or research-application package.

## Untrusted content

Indexed text and query text are untrusted data. Content that resembles an
instruction, tool request, credential prompt, or policy statement has no
execution authority. Search does not execute retrieved content.

A later generation threat model must cover prompt injection, data egress, query
logging, and citation forgery before agent or API generation is enabled.

## Acceptance evidence

`SEARCH-EVIDENCE-01` is ready for acceptance when tests demonstrate:

- deterministic identity independent of display order and process state;
- exact source resolution for every evidence kind implemented;
- fail-closed behavior for missing or inconsistent source evidence;
- explicit candidate status and uncertainty preservation;
- deterministic equal-score ordering;
- bounds at all construction and serialization layers;
- distinct insufficiency and infrastructure-failure outcomes;
- unknown-field rejection at external boundaries;
- package import without framework or model-runtime dependencies; and
- full unit, lint, type, build, and isolated-install validation.

Passing these checks establishes a software contract, not retrieval quality or
scientific correctness.

## Deferred decisions

This contract does not select:

- retrieval-unit granularity;
- lexical storage or BM25 implementation;
- embedding model or vector store;
- equation admission thresholds;
- fusion parameters;
- corpus-specific relevance judgments;
- API representations; or
- generation and refusal behavior.

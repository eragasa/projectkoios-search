# `MongoPageProjectionLexicalRetriever`

`MongoPageProjectionLexicalRetriever` resolves one validated active ready
generation, tokenizes a bounded query with the generation's exact tokenizer,
and loads at most the request ceiling plus one posting sentinel. Exceeding the
ceiling fails rather than truncates.

It computes fixed-parameter BM25 from immutable corpus/term statistics and
postings, sorts by descending score then ascending chunk ID, applies the result
limit, and returns generation-bound hits. It performs no text search service,
`mongot`, vector, embedding, model, API, workflow, or application behavior.

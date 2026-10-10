"""MongoDB projection and retrieval for page-projection lexical chunks.

The adapter stores immutable generation-scoped chunk, posting, statistic, and
metadata documents. A verified ready generation becomes visible through one
single-document active-pointer compare-and-set. The injected database owns
connection, authentication, topology, and environment selection.

Notes
-----
This module imports only Search-owned backend-neutral lexical contracts and the
MongoDB driver. It imports no Ingestion contract, concrete chunking module,
credential source, machine path, API, model, vector, or application package.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from itertools import islice
from typing import ClassVar, cast

from projectkoios.search.page_projection_lexical import (
    PageProjectionLexicalChunk,
    PageProjectionLexicalGeneration,
    PageProjectionLexicalIdentity,
    PageProjectionLexicalSearchHit,
    PageProjectionLexicalSearchRequest,
    PageProjectionLexicalSearchResult,
    PageProjectionLexicalTokenizer,
)
from pymongo import ASCENDING, IndexModel, UpdateOne
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, PyMongoError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

__all__: tuple[str, ...] = (
    "MongoPageProjectionLexicalError",
    "MongoPageProjectionLexicalProjector",
    "MongoPageProjectionLexicalRetriever",
)

MongoDocument = dict[str, object]


def _canonical_digest(value: object) -> str:
    """Return SHA-256 of compact sorted JSON-compatible material.

    Parameters
    ----------
    value
        JSON-compatible deterministic value.

    Returns
    -------
    str
        Lowercase SHA-256 digest.
    """

    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8", errors="strict")
    return hashlib.sha256(encoded).hexdigest()


def _document_id(*, kind: str, values: tuple[str, ...]) -> str:
    """Return one deterministic Mongo document identity.

    Parameters
    ----------
    kind
        Closed logical document kind.
    values
        Ordered semantic identity components.

    Returns
    -------
    str
        Prefixed digest identity safe for Mongo ``_id``.
    """

    return f"{kind}:sha256:{_canonical_digest((kind, values))}"


def _require_identity(*, value: object, label: str) -> str:
    """Return one exact bounded identity string.

    Parameters
    ----------
    value
        Candidate runtime value.
    label
        Human-readable field name for errors.

    Returns
    -------
    str
        Unchanged validated identity.
    """

    if type(value) is not str or not value:
        raise MongoPageProjectionLexicalError(
            f"{label} must be a nonempty built-in string"
        )
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise MongoPageProjectionLexicalError(
            f"{label} must be valid UTF-8"
        ) from error
    if len(encoded) > 1_024:
        raise MongoPageProjectionLexicalError(f"{label} exceeds its byte limit")
    return value


def _without_storage_fields(document: Mapping[str, object]) -> MongoDocument:
    """Return canonical logical content without generation storage keys.

    Parameters
    ----------
    document
        Persisted generation-scoped document.

    Returns
    -------
    dict[str, object]
        Copy without ``_id`` and ``generation_id``.
    """

    return {
        key: value
        for key, value in document.items()
        if key not in {"_id", "generation_id"}
    }


class MongoPageProjectionLexicalError(RuntimeError):
    """Report fail-closed lexical persistence or retrieval failure."""


class _MongoPageProjectionLexicalBase:
    """Share injected Mongo collections and generation reconstruction."""

    CHUNKS_COLLECTION: ClassVar[str] = "page_projection_chunks"
    POSTINGS_COLLECTION: ClassVar[str] = "lexical_term_postings"
    STATISTICS_COLLECTION: ClassVar[str] = "lexical_statistics"
    GENERATIONS_COLLECTION: ClassVar[str] = "lexical_generations"
    SCHEMA_ID: ClassVar[str] = (
        "projectkoios.search.mongodb-page-projection-lexical-index:1.0"
    )
    BM25_K1: ClassVar[float] = 1.2
    BM25_B: ClassVar[float] = 0.75
    _GENERATION_METADATA_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "_id",
            "document_type",
            "status",
            "storage_target_id",
            "corpus_id",
            "index_id",
            "schema_id",
            "tokenizer_id",
            "projector_id",
            "chunk_manifest_sha256",
            "index_manifest_sha256",
            "chunk_count",
            "posting_count",
            "term_count",
            "total_document_length",
        }
    )
    _ACTIVE_POINTER_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "_id",
            "document_type",
            "generation_id",
            "corpus_id",
            "index_id",
            "schema_id",
            "storage_target_id",
            "revision",
        }
    )

    def __init__(
        self,
        *,
        database: Database[MongoDocument],
        storage_target_id: str,
    ) -> None:
        """Bind an injected database and opaque storage target identity.

        Parameters
        ----------
        database
            Already connected and authenticated Mongo database capability.
        storage_target_id
            Opaque deployment identity containing no endpoint or credentials.
        """

        if not callable(getattr(database, "get_collection", None)):
            raise TypeError("database must provide Mongo collection capability")
        self._database = database
        self._storage_target_id = _require_identity(
            value=storage_target_id,
            label="storage target ID",
        )
        self._tokenizer = PageProjectionLexicalTokenizer()

    def _collection(self, *, name: str) -> Collection[MongoDocument]:
        """Return one majority-read/majority-write collection capability.

        Parameters
        ----------
        name
            Exact fixed collection name.

        Returns
        -------
        pymongo.collection.Collection
            Injected collection with explicit concerns.
        """

        collection = self._database.get_collection(name)
        return collection.with_options(
            read_concern=ReadConcern("majority"),
            write_concern=WriteConcern(w="majority"),
        )

    @property
    def _chunks(self) -> Collection[MongoDocument]:
        """Return the exact-chunk collection."""

        return self._collection(name=self.CHUNKS_COLLECTION)

    @property
    def _postings(self) -> Collection[MongoDocument]:
        """Return the term-posting collection."""

        return self._collection(name=self.POSTINGS_COLLECTION)

    @property
    def _statistics(self) -> Collection[MongoDocument]:
        """Return the lexical-statistic collection."""

        return self._collection(name=self.STATISTICS_COLLECTION)

    @property
    def _generations(self) -> Collection[MongoDocument]:
        """Return the generation-metadata collection."""

        return self._collection(name=self.GENERATIONS_COLLECTION)

    @staticmethod
    def _generation_from_metadata(
        metadata: Mapping[str, object],
    ) -> PageProjectionLexicalGeneration:
        """Reconstruct and revalidate immutable generation metadata.

        Parameters
        ----------
        metadata
            Persisted generation metadata document.

        Returns
        -------
        PageProjectionLexicalGeneration
            Exact backend-neutral generation value.
        """

        try:
            generation = PageProjectionLexicalGeneration(
                corpus_id=cast(str, metadata["corpus_id"]),
                index_id=cast(str, metadata["index_id"]),
                schema_id=cast(str, metadata["schema_id"]),
                tokenizer_id=cast(str, metadata["tokenizer_id"]),
                projector_id=cast(str, metadata["projector_id"]),
                chunk_manifest_sha256=cast(
                    str, metadata["chunk_manifest_sha256"]
                ),
                index_manifest_sha256=cast(
                    str, metadata["index_manifest_sha256"]
                ),
                chunk_count=cast(int, metadata["chunk_count"]),
                posting_count=cast(int, metadata["posting_count"]),
                term_count=cast(int, metadata["term_count"]),
                total_document_length=cast(
                    int, metadata["total_document_length"]
                ),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise MongoPageProjectionLexicalError(
                "generation metadata is malformed"
            ) from error
        if metadata.get("_id") != generation.generation_id:
            raise MongoPageProjectionLexicalError(
                "generation metadata identity is stale"
            )
        return generation

    def _ready_generation(
        self, *, generation_id: str
    ) -> PageProjectionLexicalGeneration:
        """Return one exact ready generation from persistent metadata.

        Parameters
        ----------
        generation_id
            Expected immutable generation identity.

        Returns
        -------
        PageProjectionLexicalGeneration
            Revalidated ready generation.
        """

        metadata = self._generations.find_one({"_id": generation_id})
        if metadata is None or metadata.get("status") != "ready":
            raise MongoPageProjectionLexicalError(
                "generation is absent or not ready"
            )
        if (
            frozenset(metadata) != self._GENERATION_METADATA_KEYS
            or metadata.get("document_type") != "lexical-generation"
            or metadata.get("storage_target_id") != self._storage_target_id
        ):
            raise MongoPageProjectionLexicalError(
                "generation metadata differs from its storage contract"
            )
        return self._generation_from_metadata(metadata)

    def active_generation(self) -> PageProjectionLexicalGeneration | None:
        """Return the exact active ready generation, if any.

        Returns
        -------
        PageProjectionLexicalGeneration | None
            Active generation or ``None`` before first activation.
        """

        pointer = self._generations.find_one({"_id": "active"})
        if pointer is None:
            return None
        generation_id = pointer.get("generation_id")
        if type(generation_id) is not str:
            raise MongoPageProjectionLexicalError(
                "active generation pointer is malformed"
            )
        generation = self._ready_generation(generation_id=generation_id)
        if (
            generation.schema_id != self.SCHEMA_ID
            or generation.tokenizer_id != self._tokenizer.tokenizer_id
            or generation.index_id
            != PageProjectionLexicalIdentity.index_id(
                corpus_id=generation.corpus_id,
                tokenizer_id=generation.tokenizer_id,
                schema_id=generation.schema_id,
                bm25_k1=self.BM25_K1,
                bm25_b=self.BM25_B,
            )
        ):
            raise MongoPageProjectionLexicalError(
                "active generation uses an unsupported lexical contract"
            )
        if (
            frozenset(pointer) != self._ACTIVE_POINTER_KEYS
            or pointer.get("document_type") != "active-generation-pointer"
            or pointer.get("index_id") != generation.index_id
            or pointer.get("corpus_id") != generation.corpus_id
            or pointer.get("schema_id") != generation.schema_id
            or pointer.get("storage_target_id") != self._storage_target_id
        ):
            raise MongoPageProjectionLexicalError(
                "active generation pointer bindings are stale"
            )
        revision = pointer.get("revision")
        if type(revision) is not int or revision < 1:
            raise MongoPageProjectionLexicalError(
                "active generation pointer revision is malformed"
            )
        return generation


class MongoPageProjectionLexicalProjector(_MongoPageProjectionLexicalBase):
    """Stage, verify, and atomically activate immutable lexical generations.

    Notes
    -----
    Generation-scoped writes are idempotent ``$setOnInsert`` upserts. They are
    never visible to retrieval until complete verification succeeds and the
    single active-pointer document changes through compare-and-set.
    """

    PROJECTOR_ID: ClassVar[str] = (
        "projectkoios.search.mongodb-page-projection-lexical-indexer:1.0"
    )
    MAXIMUM_CHUNKS: ClassVar[int] = 1_000_000
    MAXIMUM_POSTINGS: ClassVar[int] = 100_000_000
    MAXIMUM_TERMS: ClassVar[int] = 10_000_000
    WRITE_BATCH_SIZE: ClassVar[int] = 1_000

    def ensure_indexes(self) -> None:
        """Create and verify the exact required persistent indexes.

        Raises
        ------
        MongoPageProjectionLexicalError
            If Mongo rejects index creation or expected index definitions are
            absent afterward.
        """

        try:
            self._chunks.create_indexes(
                [
                    IndexModel(
                        (("generation_id", ASCENDING), ("chunk_id", ASCENDING)),
                        name="generation_chunk_unique",
                        unique=True,
                    ),
                ]
            )
            self._postings.create_indexes(
                [
                    IndexModel(
                        (
                            ("generation_id", ASCENDING),
                            ("term", ASCENDING),
                            ("chunk_id", ASCENDING),
                        ),
                        name="generation_term_chunk_unique",
                        unique=True,
                    ),
                ]
            )
            chunk_indexes = self._chunks.index_information()
            posting_indexes = self._postings.index_information()
        except PyMongoError as error:
            raise MongoPageProjectionLexicalError(
                "Mongo index creation or listing failed"
            ) from error
        chunk_index = chunk_indexes.get("generation_chunk_unique")
        posting_index = posting_indexes.get("generation_term_chunk_unique")
        if (
            chunk_index is None
            or tuple(chunk_index.get("key", ()))
            != (("generation_id", 1), ("chunk_id", 1))
            or chunk_index.get("unique") is not True
            or posting_index is None
            or tuple(posting_index.get("key", ()))
            != (
                ("generation_id", 1),
                ("term", 1),
                ("chunk_id", 1),
            )
            or posting_index.get("unique") is not True
        ):
            raise MongoPageProjectionLexicalError(
                "required Mongo indexes are incomplete or incompatible"
            )

    def stage(
        self,
        *,
        chunks: Iterable[PageProjectionLexicalChunk],
    ) -> PageProjectionLexicalGeneration:
        """Build and verify one immutable inactive lexical generation.

        Parameters
        ----------
        chunks
            Exact Search page-projection chunk outputs through the structural
            read-only contract.

        Returns
        -------
        PageProjectionLexicalGeneration
            Verified ready generation not yet made active.

        Raises
        ------
        MongoPageProjectionLexicalError
            If input, persistence, or complete-generation verification fails.
        """

        self.ensure_indexes()
        try:
            values = tuple(islice(iter(chunks), self.MAXIMUM_CHUNKS + 1))
        except TypeError as error:
            raise MongoPageProjectionLexicalError(
                "chunks must be an iterable structural corpus"
            ) from error
        if len(values) > self.MAXIMUM_CHUNKS:
            raise MongoPageProjectionLexicalError(
                "chunk corpus exceeds its fixed count bound"
            )
        if any(
            not isinstance(value, PageProjectionLexicalChunk)
            for value in values
        ):
            raise MongoPageProjectionLexicalError(
                "chunks must satisfy PageProjectionLexicalChunk"
            )
        try:
            (
                generation,
                chunk_documents,
                posting_documents,
                statistic_documents,
                metadata,
            ) = self._derive_documents(chunks=values)
        except (TypeError, ValueError) as error:
            raise MongoPageProjectionLexicalError(
                "chunk corpus validation failed"
            ) from error
        self._upsert_immutable(
            collection=self._generations, documents=(metadata,)
        )
        self._upsert_immutable(
            collection=self._chunks,
            documents=chunk_documents,
        )
        self._upsert_immutable(
            collection=self._postings,
            documents=posting_documents,
        )
        self._upsert_immutable(
            collection=self._statistics,
            documents=statistic_documents,
        )
        self._verify_persisted_generation(generation=generation)
        status = self._generations.update_one(
            {"_id": generation.generation_id, "status": "staging"},
            {"$set": {"status": "ready"}},
        )
        if status.matched_count == 0:
            existing = self._generations.find_one(
                {"_id": generation.generation_id}
            )
            if existing is None or existing.get("status") != "ready":
                raise MongoPageProjectionLexicalError(
                    "generation readiness transition failed"
                )
        self._verify_persisted_generation(generation=generation)
        return generation

    def activate(
        self,
        *,
        generation: PageProjectionLexicalGeneration,
        expected_active_generation_id: str | None,
    ) -> PageProjectionLexicalGeneration:
        """Atomically switch the active generation through compare-and-set.

        Parameters
        ----------
        generation
            Exact previously staged generation to activate.
        expected_active_generation_id
            Current active identity expected by the caller, or ``None`` for
            first activation.

        Returns
        -------
        PageProjectionLexicalGeneration
            Newly active generation.
        """

        if type(generation) is not PageProjectionLexicalGeneration:
            raise TypeError(
                "generation must be PageProjectionLexicalGeneration"
            )
        if expected_active_generation_id is not None:
            _require_identity(
                value=expected_active_generation_id,
                label="expected active generation ID",
            )
        persisted = self._ready_generation(
            generation_id=generation.generation_id
        )
        if persisted != generation:
            raise MongoPageProjectionLexicalError(
                "activation generation differs from persisted metadata"
            )
        # Full content verification immediately before the pointer CAS prevents
        # activation of modified or incomplete staging documents.
        self._verify_persisted_generation(generation=generation)
        current = self.active_generation()
        pointer = self._generations.find_one({"_id": "active"})
        replacement = {
            "document_type": "active-generation-pointer",
            "generation_id": generation.generation_id,
            "corpus_id": generation.corpus_id,
            "index_id": generation.index_id,
            "schema_id": generation.schema_id,
            "storage_target_id": self._storage_target_id,
        }
        if expected_active_generation_id is None:
            if current is not None or pointer is not None:
                raise MongoPageProjectionLexicalError(
                    "active generation compare-and-set failed"
                )
            try:
                self._generations.insert_one(
                    {"_id": "active", "revision": 1, **replacement}
                )
            except (DuplicateKeyError, PyMongoError) as error:
                raise MongoPageProjectionLexicalError(
                    "active generation compare-and-set failed"
                ) from error
            return generation
        if (
            current is None
            or current.generation_id != expected_active_generation_id
            or pointer is None
            or pointer.get("generation_id") != expected_active_generation_id
        ):
            raise MongoPageProjectionLexicalError(
                "active generation compare-and-set failed"
            )
        revision = pointer.get("revision")
        if type(revision) is not int or revision < 1:
            raise MongoPageProjectionLexicalError(
                "active generation pointer revision is malformed"
            )
        result = self._generations.update_one(
            {
                "_id": "active",
                "generation_id": expected_active_generation_id,
                "revision": revision,
            },
            {"$set": replacement, "$inc": {"revision": 1}},
        )
        if result.matched_count != 1:
            raise MongoPageProjectionLexicalError(
                "active generation compare-and-set failed"
            )
        return generation

    def rebuild(
        self,
        *,
        chunks: Iterable[PageProjectionLexicalChunk],
        expected_active_generation_id: str | None,
    ) -> PageProjectionLexicalGeneration:
        """Stage, verify, and activate one clean deterministic rebuild.

        Parameters
        ----------
        chunks
            Complete exact Search chunk corpus.
        expected_active_generation_id
            Expected current active generation for the pointer CAS.

        Returns
        -------
        PageProjectionLexicalGeneration
            Newly active generation.
        """

        generation = self.stage(chunks=chunks)
        return self.activate(
            generation=generation,
            expected_active_generation_id=expected_active_generation_id,
        )

    def _derive_documents(
        self,
        *,
        chunks: tuple[PageProjectionLexicalChunk, ...],
    ) -> tuple[
        PageProjectionLexicalGeneration,
        tuple[MongoDocument, ...],
        tuple[MongoDocument, ...],
        tuple[MongoDocument, ...],
        MongoDocument,
    ]:
        """Derive canonical generation metadata and all logical documents."""

        chunk_ids = tuple(value.chunk_id for value in chunks)
        manifest = PageProjectionLexicalIdentity.chunk_manifest(
            chunk_ids=chunk_ids
        )
        by_identity = {value.chunk_id: value for value in chunks}
        ordered_chunks = tuple(by_identity[value] for value in manifest)
        base_chunks: list[MongoDocument] = []
        base_postings: list[MongoDocument] = []
        document_frequencies: Counter[str] = Counter()
        total_document_length = 0
        for chunk in ordered_chunks:
            chunk_document, tokens = self._chunk_document(chunk=chunk)
            base_chunks.append(chunk_document)
            counts = Counter(tokens)
            total_document_length += len(tokens)
            document_frequencies.update(counts.keys())
            base_postings.extend(
                {
                    "document_type": "term-posting",
                    "term": term,
                    "chunk_id": chunk.chunk_id,
                    "term_frequency": frequency,
                    "document_length": len(tokens),
                }
                for term, frequency in sorted(counts.items())
            )
        base_postings.sort(
            key=lambda value: (
                cast(str, value["term"]),
                cast(str, value["chunk_id"]),
            )
        )
        if len(base_postings) > self.MAXIMUM_POSTINGS:
            raise MongoPageProjectionLexicalError(
                "posting inventory exceeds its fixed count bound"
            )
        if len(document_frequencies) > self.MAXIMUM_TERMS:
            raise MongoPageProjectionLexicalError(
                "term inventory exceeds its fixed count bound"
            )
        average_length = (
            total_document_length / len(ordered_chunks)
            if ordered_chunks
            else 0.0
        )
        base_statistics: list[MongoDocument] = [
            {
                "document_type": "corpus-statistic",
                "document_count": len(ordered_chunks),
                "total_document_length": total_document_length,
                "average_document_length_hex": average_length.hex(),
            }
        ]
        base_statistics.extend(
            {
                "document_type": "term-statistic",
                "term": term,
                "document_frequency": frequency,
            }
            for term, frequency in sorted(document_frequencies.items())
        )
        corpus_id = PageProjectionLexicalIdentity.corpus_id(chunk_ids=chunk_ids)
        index_id = PageProjectionLexicalIdentity.index_id(
            corpus_id=corpus_id,
            tokenizer_id=self._tokenizer.tokenizer_id,
            schema_id=self.SCHEMA_ID,
            bm25_k1=self.BM25_K1,
            bm25_b=self.BM25_B,
        )
        index_manifest_sha256 = _canonical_digest(
            {
                "chunks": base_chunks,
                "postings": base_postings,
                "statistics": base_statistics,
            }
        )
        generation = PageProjectionLexicalGeneration(
            corpus_id=corpus_id,
            index_id=index_id,
            schema_id=self.SCHEMA_ID,
            tokenizer_id=self._tokenizer.tokenizer_id,
            projector_id=self.PROJECTOR_ID,
            chunk_manifest_sha256=(
                PageProjectionLexicalIdentity.chunk_manifest_sha256(
                    chunk_ids=chunk_ids
                )
            ),
            index_manifest_sha256=index_manifest_sha256,
            chunk_count=len(base_chunks),
            posting_count=len(base_postings),
            term_count=len(document_frequencies),
            total_document_length=total_document_length,
        )
        chunk_documents = tuple(
            self._generation_document(
                generation_id=generation.generation_id,
                kind="page-projection-chunk",
                identity_values=(cast(str, value["chunk_id"]),),
                content=value,
            )
            for value in base_chunks
        )
        posting_documents = tuple(
            self._generation_document(
                generation_id=generation.generation_id,
                kind="term-posting",
                identity_values=(
                    cast(str, value["term"]),
                    cast(str, value["chunk_id"]),
                ),
                content=value,
            )
            for value in base_postings
        )
        statistic_documents = tuple(
            self._generation_document(
                generation_id=generation.generation_id,
                kind=cast(str, value["document_type"]),
                identity_values=(cast(str, value.get("term", "corpus")),),
                content=value,
            )
            for value in base_statistics
        )
        metadata = self._generation_metadata(generation=generation)
        return (
            generation,
            chunk_documents,
            posting_documents,
            statistic_documents,
            metadata,
        )

    def _chunk_document(
        self, *, chunk: PageProjectionLexicalChunk
    ) -> tuple[MongoDocument, tuple[str, ...]]:
        """Validate one structural chunk and project exact stored fields."""

        identity_fields = {
            "chunk_id": chunk.chunk_id,
            "page_projection_result_id": chunk.page_projection_result_id,
            "source_id": chunk.source_id,
            "document_id": chunk.document_id,
            "source_result_id": chunk.source_result_id,
            "artifact_verification_result_id": (
                chunk.artifact_verification_result_id
            ),
            "reading_projection_result_id": (
                chunk.reading_projection_result_id
            ),
            "reading_inventory_id": chunk.reading_inventory_id,
            "page_projection_page_id": chunk.page_projection_page_id,
            "source_page_id": chunk.source_page_id,
            "page_location_id": chunk.page_location_id,
            "page_projection_block_id": chunk.page_projection_block_id,
            "source_evidence_id": chunk.source_evidence_id,
        }
        for label, value in identity_fields.items():
            _require_identity(value=value, label=label.replace("_", " "))
        if type(chunk.physical_page_index) is not int or (
            chunk.physical_page_index < 0
        ):
            raise MongoPageProjectionLexicalError(
                "physical page index must be nonnegative"
            )
        if (
            type(chunk.physical_page_number) is not int
            or chunk.physical_page_number != chunk.physical_page_index + 1
        ):
            raise MongoPageProjectionLexicalError(
                "physical page number differs from its index"
            )
        if type(chunk.order_index) is not int or chunk.order_index < 0:
            raise MongoPageProjectionLexicalError(
                "order index must be nonnegative"
            )
        if chunk.printed_page_label is not None:
            _require_identity(
                value=chunk.printed_page_label,
                label="printed page label",
            )
        style = getattr(chunk.style, "value", None)
        if style not in {"paragraph", "heading", "figure_caption"}:
            raise MongoPageProjectionLexicalError("chunk style is unsupported")
        if type(chunk.text) is not str or not chunk.text:
            raise MongoPageProjectionLexicalError(
                "chunk text must be a nonempty built-in string"
            )
        try:
            encoded = chunk.text.encode("utf-8", errors="strict")
        except UnicodeEncodeError as error:
            raise ValueError("chunk text must be valid UTF-8") from error
        digest = hashlib.sha256(encoded).hexdigest()
        if (
            digest != chunk.text_sha256
            or type(chunk.text_utf8_bytes) is not int
            or len(encoded) != chunk.text_utf8_bytes
        ):
            raise MongoPageProjectionLexicalError(
                "chunk text measures are stale"
            )
        tokens = self._tokenizer.tokens(text=chunk.text)
        return (
            {
                "document_type": "page-projection-chunk",
                **identity_fields,
                "physical_page_index": chunk.physical_page_index,
                "physical_page_number": chunk.physical_page_number,
                "printed_page_label": chunk.printed_page_label,
                "order_index": chunk.order_index,
                "style": style,
                "text": chunk.text,
                "text_sha256": chunk.text_sha256,
                "text_utf8_bytes": chunk.text_utf8_bytes,
                "document_length": len(tokens),
            },
            tokens,
        )

    @staticmethod
    def _generation_document(
        *,
        generation_id: str,
        kind: str,
        identity_values: tuple[str, ...],
        content: Mapping[str, object],
    ) -> MongoDocument:
        """Attach generation scope and deterministic storage identity."""

        return {
            "_id": _document_id(
                kind=kind,
                values=(generation_id, *identity_values),
            ),
            "generation_id": generation_id,
            **content,
        }

    def _generation_metadata(
        self, *, generation: PageProjectionLexicalGeneration
    ) -> MongoDocument:
        """Return deterministic staging metadata for one generation."""

        return {
            "_id": generation.generation_id,
            "document_type": "lexical-generation",
            "status": "staging",
            "storage_target_id": self._storage_target_id,
            "corpus_id": generation.corpus_id,
            "index_id": generation.index_id,
            "schema_id": generation.schema_id,
            "tokenizer_id": generation.tokenizer_id,
            "projector_id": generation.projector_id,
            "chunk_manifest_sha256": generation.chunk_manifest_sha256,
            "index_manifest_sha256": generation.index_manifest_sha256,
            "chunk_count": generation.chunk_count,
            "posting_count": generation.posting_count,
            "term_count": generation.term_count,
            "total_document_length": generation.total_document_length,
        }

    def _upsert_immutable(
        self,
        *,
        collection: Collection[MongoDocument],
        documents: Sequence[MongoDocument],
    ) -> None:
        """Idempotently insert immutable documents in bounded write batches."""

        try:
            for offset in range(0, len(documents), self.WRITE_BATCH_SIZE):
                batch = documents[offset : offset + self.WRITE_BATCH_SIZE]
                if not batch:
                    continue
                collection.bulk_write(
                    [
                        UpdateOne(
                            {"_id": document["_id"]},
                            {"$setOnInsert": document},
                            upsert=True,
                        )
                        for document in batch
                    ],
                    ordered=True,
                )
        except PyMongoError as error:
            raise MongoPageProjectionLexicalError(
                "immutable Mongo staging write failed"
            ) from error

    def _verify_persisted_generation(
        self, *, generation: PageProjectionLexicalGeneration
    ) -> None:
        """Verify complete stored documents against immutable generation IDs."""

        metadata = self._generations.find_one({"_id": generation.generation_id})
        if metadata is None:
            raise MongoPageProjectionLexicalError(
                "generation verification found no metadata"
            )
        persisted = self._generation_from_metadata(metadata)
        status = metadata.get("status")
        expected_metadata = self._generation_metadata(generation=generation)
        expected_metadata["status"] = status
        if (
            persisted != generation
            or status not in {"staging", "ready"}
            or metadata != expected_metadata
        ):
            raise MongoPageProjectionLexicalError(
                "generation verification found different metadata"
            )
        chunks = tuple(
            self._chunks.find(
                {"generation_id": generation.generation_id},
                sort=[("_id", ASCENDING)],
            )
        )
        postings = tuple(
            self._postings.find(
                {"generation_id": generation.generation_id},
                sort=[("_id", ASCENDING)],
            )
        )
        statistics = tuple(
            self._statistics.find(
                {"generation_id": generation.generation_id},
                sort=[("_id", ASCENDING)],
            )
        )
        if (
            len(chunks) != generation.chunk_count
            or len(postings) != generation.posting_count
            or len(statistics) != generation.term_count + 1
        ):
            raise MongoPageProjectionLexicalError(
                "generation verification found incomplete document counts"
            )
        for document in chunks:
            if document.get("_id") != _document_id(
                kind="page-projection-chunk",
                values=(
                    generation.generation_id,
                    cast(str, document.get("chunk_id")),
                ),
            ):
                raise MongoPageProjectionLexicalError(
                    "generation verification found a stale chunk identity"
                )
        for document in postings:
            if document.get("_id") != _document_id(
                kind="term-posting",
                values=(
                    generation.generation_id,
                    cast(str, document.get("term")),
                    cast(str, document.get("chunk_id")),
                ),
            ):
                raise MongoPageProjectionLexicalError(
                    "generation verification found a stale posting identity"
                )
        for document in statistics:
            kind = document.get("document_type")
            if kind not in {"corpus-statistic", "term-statistic"} or (
                document.get("_id")
                != _document_id(
                    kind=kind,
                    values=(
                        generation.generation_id,
                        cast(str, document.get("term", "corpus")),
                    ),
                )
            ):
                raise MongoPageProjectionLexicalError(
                    "generation verification found a stale statistic identity"
                )
        logical_chunks = tuple(
            _without_storage_fields(value) for value in chunks
        )
        logical_postings = tuple(
            _without_storage_fields(value) for value in postings
        )
        logical_statistics = tuple(
            _without_storage_fields(value) for value in statistics
        )
        observed_digest = _canonical_digest(
            {
                "chunks": sorted(
                    logical_chunks,
                    key=lambda value: cast(str, value["chunk_id"]),
                ),
                "postings": sorted(
                    logical_postings,
                    key=lambda value: (
                        cast(str, value["term"]),
                        cast(str, value["chunk_id"]),
                    ),
                ),
                "statistics": sorted(
                    logical_statistics,
                    key=lambda value: (
                        cast(str, value["document_type"]),
                        cast(str, value.get("term", "")),
                    ),
                ),
            }
        )
        if observed_digest != generation.index_manifest_sha256:
            raise MongoPageProjectionLexicalError(
                "generation verification found altered document content"
            )


class MongoPageProjectionLexicalRetriever(_MongoPageProjectionLexicalBase):
    """Run bounded deterministic BM25 over the active Mongo generation."""

    RETRIEVER_ID: ClassVar[str] = (
        "projectkoios.search.mongodb-page-projection-bm25-retriever:1.0"
    )
    MAXIMUM_QUERY_TERMS: ClassVar[int] = (
        PageProjectionLexicalSearchRequest.MAXIMUM_QUERY_TERMS
    )

    def search(
        self, *, request: PageProjectionLexicalSearchRequest
    ) -> PageProjectionLexicalSearchResult:
        """Return stable bounded hits from one active generation snapshot.

        Parameters
        ----------
        request
            Exact bounded lexical search request.

        Returns
        -------
        PageProjectionLexicalSearchResult
            Deterministic score-descending, chunk-identity-tied result.
        """

        if type(request) is not PageProjectionLexicalSearchRequest:
            raise TypeError(
                "request must be PageProjectionLexicalSearchRequest"
            )
        generation = self.active_generation()
        if generation is None:
            raise MongoPageProjectionLexicalError(
                "active generation is required for retrieval"
            )
        query_terms = self._tokenizer.query_terms(text=request.query)
        if len(query_terms) > self.MAXIMUM_QUERY_TERMS:
            raise MongoPageProjectionLexicalError(
                "query exceeds its fixed lexical term bound"
            )
        if not query_terms:
            return PageProjectionLexicalSearchResult(
                request=request,
                generation=generation,
                retriever_id=self.RETRIEVER_ID,
                normalized_query_terms=(),
                hits=(),
            )
        cursor = self._postings.find(
            {
                "generation_id": generation.generation_id,
                "term": {"$in": list(query_terms)},
            },
            limit=request.maximum_candidate_postings + 1,
        )
        postings = tuple(cursor)
        if len(postings) > request.maximum_candidate_postings:
            raise MongoPageProjectionLexicalError(
                "candidate posting bound exceeded"
            )
        corpus_statistic_id = _document_id(
            kind="corpus-statistic",
            values=(generation.generation_id, "corpus"),
        )
        corpus_statistic = self._statistics.find_one(
            {"_id": corpus_statistic_id}
        )
        if corpus_statistic is None:
            raise MongoPageProjectionLexicalError(
                "active generation corpus statistics are missing"
            )
        document_count = corpus_statistic.get("document_count")
        average_hex = corpus_statistic.get("average_document_length_hex")
        if type(document_count) is not int or type(average_hex) is not str:
            raise MongoPageProjectionLexicalError(
                "active generation corpus statistics are malformed"
            )
        try:
            average_document_length = float.fromhex(average_hex)
        except ValueError as error:
            raise MongoPageProjectionLexicalError(
                "active generation average length is malformed"
            ) from error
        document_frequencies: dict[str, int] = {}
        for term in query_terms:
            statistic_id = _document_id(
                kind="term-statistic",
                values=(generation.generation_id, term),
            )
            statistic = self._statistics.find_one({"_id": statistic_id})
            if statistic is None:
                document_frequencies[term] = 0
                continue
            frequency = statistic.get("document_frequency")
            if (
                type(frequency) is not int
                or not 0 <= frequency <= document_count
            ):
                raise MongoPageProjectionLexicalError(
                    "term document frequency is malformed"
                )
            document_frequencies[term] = frequency
        by_chunk: defaultdict[str, dict[str, int]] = defaultdict(dict)
        lengths: dict[str, int] = {}
        for posting in postings:
            posting_term = posting.get("term")
            chunk_id = posting.get("chunk_id")
            frequency = posting.get("term_frequency")
            length = posting.get("document_length")
            if (
                type(posting_term) is not str
                or posting_term not in query_terms
                or type(chunk_id) is not str
                or type(frequency) is not int
                or frequency < 1
                or type(length) is not int
                or length < 1
            ):
                raise MongoPageProjectionLexicalError(
                    "candidate posting is malformed"
                )
            if chunk_id in lengths and lengths[chunk_id] != length:
                raise MongoPageProjectionLexicalError(
                    "candidate posting lengths disagree"
                )
            lengths[chunk_id] = length
            by_chunk[chunk_id][posting_term] = frequency
        scored: list[tuple[str, float, tuple[str, ...]]] = []
        for chunk_id, frequencies in by_chunk.items():
            matched_terms = tuple(
                term for term in query_terms if term in frequencies
            )
            score = self._bm25_score(
                query_terms=query_terms,
                frequencies=frequencies,
                document_length=lengths[chunk_id],
                document_count=document_count,
                document_frequencies=document_frequencies,
                average_document_length=average_document_length,
            )
            if score > 0.0:
                scored.append((chunk_id, score, matched_terms))
        scored.sort(key=lambda value: (-value[1], value[0]))
        hits = tuple(
            PageProjectionLexicalSearchHit(
                chunk_id=chunk_id,
                score=score,
                rank=rank,
                matched_terms=matched_terms,
            )
            for rank, (chunk_id, score, matched_terms) in enumerate(
                scored[: request.limit],
                start=1,
            )
        )
        return PageProjectionLexicalSearchResult(
            request=request,
            generation=generation,
            retriever_id=self.RETRIEVER_ID,
            normalized_query_terms=query_terms,
            hits=hits,
        )

    @classmethod
    def _bm25_score(
        cls,
        *,
        query_terms: tuple[str, ...],
        frequencies: Mapping[str, int],
        document_length: int,
        document_count: int,
        document_frequencies: Mapping[str, int],
        average_document_length: float,
    ) -> float:
        """Return the fixed BM25 score for one candidate chunk."""

        if document_count == 0 or average_document_length == 0.0:
            return 0.0
        score = 0.0
        for term in query_terms:
            term_frequency = frequencies.get(term, 0)
            if term_frequency == 0:
                continue
            document_frequency = document_frequencies[term]
            inverse_document_frequency = math.log(
                1.0
                + (document_count - document_frequency + 0.5)
                / (document_frequency + 0.5)
            )
            normalization = term_frequency + cls.BM25_K1 * (
                1.0
                - cls.BM25_B
                + cls.BM25_B * document_length / average_document_length
            )
            score += inverse_document_frequency * (
                term_frequency * (cls.BM25_K1 + 1.0) / normalization
            )
        return score

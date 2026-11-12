"""Durable, retryable OCR queue for stored document content versions.

Uploads do not block on text extraction. A clean version can be queued, an
external worker claims due jobs with a lease, and the extracted text plus the
engine identity are recorded on the same job row. The reference engine only
decodes already-textual payloads; it is not an OCR engine and returns
``unsupported`` for images/PDFs instead of fabricating text.

As with scheduled reports, there is no in-process timer. A deployment must
invoke :meth:`DocumentOcrRunner.run_due` from its external scheduler.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from .document_persistence import DocumentAuthorizationError
from .api_errors import APIError, conflict_error, persistence_error, validation_error

OCR_STATUSES = ("pending", "running", "succeeded", "failed", "skipped")
OCR_SUPPORTED_TEXT_TYPES = (
    "text/plain",
    "text/csv",
    "application/xml",
    "text/xml",
)
DEFAULT_OCR_MAX_CHARS = 200_000
DEFAULT_OCR_MAX_ATTEMPTS = 3
DEFAULT_OCR_LEASE_SECONDS = 300


class DocumentOcrError(ValueError):
    pass


# --- legacy adapter contract (kept for compatibility) ----------------------


class DocumentOCRAdapterError(ValueError):
    pass


@dataclass(frozen=True)
class OCRRequest:
    tenant_id: str
    project_id: str
    document_id: str
    revision: int
    storage_ref: str

    def validate(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("document_id", self.document_id),
            ("storage_ref", self.storage_ref),
        ):
            if not isinstance(value, str) or not value.strip():
                raise DocumentOCRAdapterError(f"INVALID_DOCUMENT_OCR_{name.upper()}")
        if (
            isinstance(self.revision, bool)
            or not isinstance(self.revision, int)
            or self.revision < 1
        ):
            raise DocumentOCRAdapterError("INVALID_DOCUMENT_OCR_REVISION")


@dataclass(frozen=True)
class OCRResult:
    tenant_id: str
    project_id: str
    document_id: str
    revision: int
    text: str
    provider: str

    def validate(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("document_id", self.document_id),
            ("provider", self.provider),
        ):
            if not isinstance(value, str) or not value.strip():
                raise DocumentOCRAdapterError(f"INVALID_DOCUMENT_OCR_{name.upper()}")
        if (
            isinstance(self.revision, bool)
            or not isinstance(self.revision, int)
            or self.revision < 1
        ):
            raise DocumentOCRAdapterError("INVALID_DOCUMENT_OCR_REVISION")
        if not isinstance(self.text, str):
            raise DocumentOCRAdapterError("INVALID_DOCUMENT_OCR_TEXT")


class DocumentOCRAdapter(Protocol):
    def extract(self, request: OCRRequest) -> OCRResult: ...


class ReferenceDocumentOCRAdapter:
    """Deterministic adapter used by tests; no OCR engine or storage access is embedded."""

    def __init__(self, extracted_text: str, provider: str = "reference") -> None:
        self.extracted_text = extracted_text
        self.provider = provider

    def extract(self, request: OCRRequest) -> OCRResult:
        request.validate()
        if not isinstance(self.extracted_text, str):
            raise DocumentOCRAdapterError("INVALID_DOCUMENT_OCR_TEXT")
        result = OCRResult(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            document_id=request.document_id,
            revision=request.revision,
            text=self.extracted_text,
            provider=self.provider,
        )
        result.validate()
        return result


# --- durable extraction queue -----------------------------------------------


class DocumentOcrNotFound(DocumentOcrError):
    pass


class DocumentOcrClaimLost(DocumentOcrError):
    pass


class DocumentOcrNotRetryable(DocumentOcrError):
    pass


class OcrUnsupported(DocumentOcrError):
    """The payload type cannot be extracted by the selected engine."""


@dataclass(frozen=True)
class OcrExtraction:
    text: str
    engine: str
    engine_version: str

    def validate(self) -> None:
        if not isinstance(self.text, str):
            raise DocumentOcrError("INVALID_DOCUMENT_OCR_TEXT")
        for name, value in (
            ("ENGINE", self.engine),
            ("ENGINE_VERSION", self.engine_version),
        ):
            if not isinstance(value, str) or not value.strip():
                raise DocumentOcrError(f"INVALID_DOCUMENT_OCR_{name}")


class DocumentOcrEngine(Protocol):
    def extract(self, data: bytes, *, content_type: str) -> OcrExtraction: ...


class ReferenceDocumentOcrEngine:
    """Decode text-like payloads only; never fabricate OCR output."""

    engine = "reference-text"
    engine_version = "1"

    def extract(self, data: bytes, *, content_type: str) -> OcrExtraction:
        if content_type not in OCR_SUPPORTED_TEXT_TYPES:
            raise OcrUnsupported("DOCUMENT_OCR_UNSUPPORTED_CONTENT_TYPE")
        if not isinstance(data, (bytes, bytearray)):
            raise DocumentOcrError("INVALID_DOCUMENT_OCR_PAYLOAD")
        text = bytes(data).decode("utf-8", "replace")
        return OcrExtraction(
            text=text, engine=self.engine, engine_version=self.engine_version
        )


def _iso(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise DocumentOcrError("INVALID_DOCUMENT_OCR_TIMESTAMP")
    return value.astimezone(timezone.utc).isoformat()


def _parse(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class DocumentOcrJob:
    tenant_id: str
    project_id: str
    document_id: str
    version: int
    storage_ref: str
    content_hash: str
    content_type: str
    byte_size: int
    original_filename: str
    requested_by: str
    requested_at: datetime
    status: str = "pending"
    attempts: int = 0
    max_attempts: int = DEFAULT_OCR_MAX_ATTEMPTS
    next_attempt_at: datetime | None = None
    claim_token: str | None = None
    claimed_until: datetime | None = None
    claimed_by: str = ""
    text: str | None = None
    char_count: int | None = None
    engine: str = ""
    engine_version: str = ""
    detail: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def validate(self) -> None:
        for name, value in (
            ("TENANT_ID", self.tenant_id),
            ("PROJECT_ID", self.project_id),
            ("DOCUMENT_ID", self.document_id),
            ("STORAGE_REF", self.storage_ref),
            ("ORIGINAL_FILENAME", self.original_filename),
            ("REQUESTED_BY", self.requested_by),
        ):
            if not isinstance(value, str) or not value.strip():
                raise DocumentOcrError(f"INVALID_DOCUMENT_OCR_{name}")
        if (
            isinstance(self.version, bool)
            or not isinstance(self.version, int)
            or self.version < 1
        ):
            raise DocumentOcrError("INVALID_DOCUMENT_OCR_VERSION")
        if not self.content_hash.startswith("sha256:") or len(self.content_hash) != 71:
            raise DocumentOcrError("INVALID_DOCUMENT_OCR_HASH")
        if not isinstance(self.content_type, str) or not self.content_type.strip():
            raise DocumentOcrError("INVALID_DOCUMENT_OCR_CONTENT_TYPE")
        if (
            isinstance(self.byte_size, bool)
            or not isinstance(self.byte_size, int)
            or self.byte_size <= 0
        ):
            raise DocumentOcrError("INVALID_DOCUMENT_OCR_SIZE")
        if self.status not in OCR_STATUSES:
            raise DocumentOcrError("INVALID_DOCUMENT_OCR_STATUS")
        for name, value in (("ATTEMPTS", self.attempts), ("MAX_ATTEMPTS", self.max_attempts)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise DocumentOcrError(f"INVALID_DOCUMENT_OCR_{name}")
        if self.max_attempts < 1:
            raise DocumentOcrError("INVALID_DOCUMENT_OCR_MAX_ATTEMPTS")
        if self.next_attempt_at is None:
            raise DocumentOcrError("INVALID_DOCUMENT_OCR_NEXT_ATTEMPT")
        if self.char_count is not None and (
            isinstance(self.char_count, bool)
            or not isinstance(self.char_count, int)
            or self.char_count < 0
        ):
            raise DocumentOcrError("INVALID_DOCUMENT_OCR_CHAR_COUNT")
        for name, value in (
            ("CLAIM_TOKEN", self.claim_token),
            ("CLAIMED_BY", self.claimed_by),
            ("ENGINE", self.engine),
            ("ENGINE_VERSION", self.engine_version),
            ("DETAIL", self.detail),
        ):
            if value is not None and not isinstance(value, str):
                raise DocumentOcrError(f"INVALID_DOCUMENT_OCR_{name}")

    def as_dict(self, *, include_text: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "document_id": self.document_id,
            "version": self.version,
            "status": self.status,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "content_hash": self.content_hash,
            "content_type": self.content_type,
            "byte_size": self.byte_size,
            "engine": self.engine,
            "engine_version": self.engine_version,
            "detail": self.detail,
            "requested_by": self.requested_by,
            "requested_at": _iso(self.requested_at),
            "next_attempt_at": _iso(self.next_attempt_at),
            "started_at": None if self.started_at is None else _iso(self.started_at),
            "completed_at": (
                None if self.completed_at is None else _iso(self.completed_at)
            ),
            "char_count": self.char_count,
        }
        if include_text:
            payload["text"] = self.text
        return payload


class DocumentOcrRepository(Protocol):
    def request(self, job: DocumentOcrJob) -> DocumentOcrJob: ...

    def get(
        self, tenant_id: str, project_id: str, document_id: str, version: int
    ) -> DocumentOcrJob | None: ...

    def list(
        self, tenant_id: str, project_id: str, document_id: str
    ) -> tuple[DocumentOcrJob, ...]: ...

    def claim_due(
        self, now: datetime, worker_id: str, limit: int
    ) -> tuple[DocumentOcrJob, ...]: ...

    def retry(
        self, tenant_id: str, project_id: str, document_id: str, version: int, now: datetime
    ) -> DocumentOcrJob: ...


class _DocumentOcrStore:
    """Shared SQL implementation; subclasses only change the placeholder."""

    placeholder = "?"
    lease_seconds = DEFAULT_OCR_LEASE_SECONDS

    def __init__(self, connection, *, lease_seconds: int | None = None) -> None:
        self.connection = connection
        if lease_seconds is not None:
            if (
                isinstance(lease_seconds, bool)
                or not isinstance(lease_seconds, int)
                or lease_seconds < 1
            ):
                raise DocumentOcrError("INVALID_DOCUMENT_OCR_LEASE")
            self.lease_seconds = lease_seconds

    @property
    def q(self) -> str:
        return self.placeholder

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_document_ocr (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                version BIGINT NOT NULL,
                status TEXT NOT NULL,
                storage_ref TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                content_type TEXT NOT NULL,
                byte_size BIGINT NOT NULL,
                original_filename TEXT NOT NULL,
                requested_by TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                attempts INTEGER NOT NULL,
                max_attempts INTEGER NOT NULL,
                next_attempt_at TEXT NOT NULL,
                claim_token TEXT,
                claimed_until TEXT,
                claimed_by TEXT NOT NULL,
                text_content TEXT,
                char_count INTEGER,
                engine TEXT NOT NULL,
                engine_version TEXT NOT NULL,
                detail TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                PRIMARY KEY (tenant_id, project_id, document_id, version)
            )"""
        )
        self.connection.execute(
            """CREATE INDEX IF NOT EXISTS project_document_ocr_due
                ON project_document_ocr (status, next_attempt_at)"""
        )

    def _row(self, row) -> DocumentOcrJob:
        return DocumentOcrJob(
            tenant_id=row[0],
            project_id=row[1],
            document_id=row[2],
            version=int(row[3]),
            status=row[4],
            storage_ref=row[5],
            content_hash=row[6],
            content_type=row[7],
            byte_size=int(row[8]),
            original_filename=row[9],
            requested_by=row[10],
            requested_at=_parse(row[11]),
            attempts=int(row[12]),
            max_attempts=int(row[13]),
            next_attempt_at=_parse(row[14]),
            claim_token=row[15],
            claimed_until=_parse(row[16]),
            claimed_by=row[17] or "",
            text=row[18],
            char_count=None if row[19] is None else int(row[19]),
            engine=row[20] or "",
            engine_version=row[21] or "",
            detail=row[22] or "",
            started_at=_parse(row[23]),
            completed_at=_parse(row[24]),
        )

    _COLUMNS = (
        "tenant_id, project_id, document_id, version, status, storage_ref, "
        "content_hash, content_type, byte_size, original_filename, requested_by, "
        "requested_at, attempts, max_attempts, next_attempt_at, claim_token, "
        "claimed_until, claimed_by, text_content, char_count, engine, "
        "engine_version, detail, started_at, completed_at"
    )

    def _fetch(self, tenant_id, project_id, document_id, version):
        rows = self.connection.execute(
            f"SELECT {self._COLUMNS} FROM project_document_ocr "
            f"WHERE tenant_id={self.q} AND project_id={self.q} "
            f"AND document_id={self.q} AND version={self.q}",
            (tenant_id, project_id, document_id, version),
        ).fetchall()
        return None if not rows else self._row(rows[0])

    def get(self, tenant_id: str, project_id: str, document_id: str, version: int):
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            return None
        return self._fetch(tenant_id, project_id, document_id, version)

    def list(self, tenant_id: str, project_id: str, document_id: str):
        rows = self.connection.execute(
            f"SELECT {self._COLUMNS} FROM project_document_ocr "
            f"WHERE tenant_id={self.q} AND project_id={self.q} "
            f"AND document_id={self.q} ORDER BY version",
            (tenant_id, project_id, document_id),
        ).fetchall()
        return tuple(self._row(row) for row in rows)

    def request(self, job: DocumentOcrJob) -> DocumentOcrJob:
        job.validate()
        self.connection.execute(
            f"""INSERT INTO project_document_ocr ({self._COLUMNS})
                VALUES ({", ".join([self.q] * 25)})
                ON CONFLICT (tenant_id, project_id, document_id, version) DO NOTHING""",
            (
                job.tenant_id,
                job.project_id,
                job.document_id,
                job.version,
                job.status,
                job.storage_ref,
                job.content_hash,
                job.content_type,
                job.byte_size,
                job.original_filename,
                job.requested_by,
                _iso(job.requested_at),
                job.attempts,
                job.max_attempts,
                _iso(job.next_attempt_at),
                job.claim_token,
                None if job.claimed_until is None else _iso(job.claimed_until),
                job.claimed_by,
                job.text,
                job.char_count,
                job.engine,
                job.engine_version,
                job.detail,
                None if job.started_at is None else _iso(job.started_at),
                None if job.completed_at is None else _iso(job.completed_at),
            ),
        )
        existing = self.get(job.tenant_id, job.project_id, job.document_id, job.version)
        if existing is None:
            raise DocumentOcrError("DOCUMENT_OCR_REQUEST_FAILED")
        return existing

    def claim_due(
        self, now: datetime, worker_id: str, limit: int
    ) -> tuple[DocumentOcrJob, ...]:
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or limit < 1
            or limit > 500
        ):
            raise DocumentOcrError("INVALID_DOCUMENT_OCR_LIMIT")
        if not isinstance(worker_id, str) or not worker_id.strip():
            raise DocumentOcrError("INVALID_DOCUMENT_OCR_WORKER")
        now_text = _iso(now)
        candidates = self.connection.execute(
            f"""SELECT tenant_id, project_id, document_id, version
                FROM project_document_ocr
                WHERE (status = 'pending' AND next_attempt_at <= {self.q})
                   OR (status = 'running' AND claimed_until IS NOT NULL
                       AND claimed_until <= {self.q})
                ORDER BY next_attempt_at, requested_at LIMIT {self.q}""",
            (now_text, now_text, limit),
        ).fetchall()
        claimed: list[DocumentOcrJob] = []
        for tenant_id, project_id, document_id, version in candidates:
            token = secrets.token_hex(16)
            until = _iso(now + timedelta(seconds=self.lease_seconds))
            cur = self.connection.execute(
                f"""UPDATE project_document_ocr
                    SET status='running', claim_token={self.q}, claimed_until={self.q},
                        claimed_by={self.q}, started_at=COALESCE(started_at, {self.q}),
                        next_attempt_at={self.q}
                    WHERE tenant_id={self.q} AND project_id={self.q}
                      AND document_id={self.q} AND version={self.q}
                      AND ((status='pending' AND next_attempt_at <= {self.q})
                        OR (status='running' AND claimed_until IS NOT NULL
                            AND claimed_until <= {self.q}))""",
                (
                    token,
                    until,
                    worker_id.strip(),
                    now_text,
                    now_text,
                    tenant_id,
                    project_id,
                    document_id,
                    version,
                    now_text,
                    now_text,
                ),
            )
            if cur.rowcount != 1:
                continue
            job = self.get(tenant_id, project_id, document_id, version)
            if job is not None:
                claimed.append(job)
        return tuple(claimed)

    def _finish(
        self,
        job: DocumentOcrJob,
        *,
        status: str,
        now: datetime,
        detail: str = "",
        text: str | None = None,
        char_count: int | None = None,
        engine: str = "",
        engine_version: str = "",
        attempts: int | None = None,
        next_attempt_at: datetime | None = None,
        completed: bool = True,
    ) -> DocumentOcrJob:
        if job.claim_token is None:
            raise DocumentOcrClaimLost("DOCUMENT_OCR_CLAIM_LOST")
        completed_at = _iso(now) if completed else None
        cur = self.connection.execute(
            f"""UPDATE project_document_ocr
                SET status={self.q}, text_content={self.q}, char_count={self.q},
                    engine={self.q}, engine_version={self.q}, detail={self.q},
                    attempts={self.q}, next_attempt_at={self.q},
                    completed_at={self.q}, claim_token=NULL, claimed_until=NULL
                WHERE tenant_id={self.q} AND project_id={self.q}
                  AND document_id={self.q} AND version={self.q}
                  AND claim_token={self.q}""",
            (
                status,
                text,
                char_count,
                engine,
                engine_version,
                detail,
                job.attempts if attempts is None else attempts,
                _iso(next_attempt_at or now),
                completed_at,
                job.tenant_id,
                job.project_id,
                job.document_id,
                job.version,
                job.claim_token,
            ),
        )
        if cur.rowcount != 1:
            raise DocumentOcrClaimLost("DOCUMENT_OCR_CLAIM_LOST")
        updated = self.get(job.tenant_id, job.project_id, job.document_id, job.version)
        if updated is None:
            raise DocumentOcrNotFound("DOCUMENT_OCR_NOT_FOUND")
        return updated

    def complete(
        self, job: DocumentOcrJob, extraction: OcrExtraction, now: datetime
    ) -> DocumentOcrJob:
        extraction.validate()
        return self._finish(
            job,
            status="succeeded",
            now=now,
            text=extraction.text,
            char_count=len(extraction.text),
            engine=extraction.engine,
            engine_version=extraction.engine_version,
        )

    def skip(self, job: DocumentOcrJob, *, detail: str, now: datetime) -> DocumentOcrJob:
        return self._finish(
            job,
            status="skipped",
            now=now,
            detail=detail,
            engine=job.engine,
            engine_version=job.engine_version,
        )

    def fail(self, job: DocumentOcrJob, *, detail: str, now: datetime) -> DocumentOcrJob:
        attempts = job.attempts + 1
        terminal = attempts >= job.max_attempts
        backoff = min(300 * (2 ** (attempts - 1)), 3600)
        return self._finish(
            job,
            status="failed" if terminal else "pending",
            now=now,
            detail=detail,
            attempts=attempts,
            next_attempt_at=now if terminal else now + timedelta(seconds=backoff),
            completed=terminal,
        )

    def retry(
        self, tenant_id: str, project_id: str, document_id: str, version: int, now: datetime
    ) -> DocumentOcrJob:
        job = self.get(tenant_id, project_id, document_id, version)
        if job is None:
            raise DocumentOcrNotFound("DOCUMENT_OCR_NOT_FOUND")
        if job.status not in {"failed", "skipped"}:
            raise DocumentOcrNotRetryable("DOCUMENT_OCR_NOT_RETRYABLE")
        self.connection.execute(
            f"""UPDATE project_document_ocr
                SET status='pending', attempts=0, next_attempt_at={self.q},
                    text_content=NULL, char_count=NULL, detail='',
                    started_at=NULL, completed_at=NULL,
                    claim_token=NULL, claimed_until=NULL, claimed_by=''
                WHERE tenant_id={self.q} AND project_id={self.q}
                  AND document_id={self.q} AND version={self.q}""",
            (now.isoformat(), tenant_id, project_id, document_id, version),
        )
        updated = self.get(tenant_id, project_id, document_id, version)
        if updated is None:
            raise DocumentOcrNotFound("DOCUMENT_OCR_NOT_FOUND")
        return updated


class SQLiteDocumentOcrRepository(_DocumentOcrStore):
    placeholder = "?"


class PostgresDocumentOcrRepository(_DocumentOcrStore):
    placeholder = "%s"


class DocumentOcrRunner:
    """Claim and execute due OCR jobs; the deployment owns the trigger."""

    def __init__(
        self,
        store: _DocumentOcrStore,
        storage,
        engine: DocumentOcrEngine,
        *,
        max_chars: int = DEFAULT_OCR_MAX_CHARS,
    ) -> None:
        if (
            isinstance(max_chars, bool)
            or not isinstance(max_chars, int)
            or max_chars < 1
        ):
            raise DocumentOcrError("INVALID_DOCUMENT_OCR_MAX_CHARS")
        self.store = store
        self.storage = storage
        self.engine = engine
        self.max_chars = max_chars

    def run_due(
        self, now: datetime, worker_id: str, limit: int = 10
    ) -> tuple[DocumentOcrJob, ...]:
        results: list[DocumentOcrJob] = []
        for job in self.store.claim_due(now, worker_id, limit):
            try:
                payload = self.storage.read(
                    job.storage_ref,
                    tenant_id=job.tenant_id,
                    project_id=job.project_id,
                    expected_content_hash=job.content_hash,
                )
                extraction = self.engine.extract(
                    payload, content_type=job.content_type
                )
                if len(extraction.text) > self.max_chars:
                    raise DocumentOcrError("DOCUMENT_OCR_TEXT_TOO_LARGE")
                results.append(self.store.complete(job, extraction, now))
            except OcrUnsupported as exc:
                results.append(
                    self.store.skip(job, detail=str(exc), now=now)
                )
            except Exception as exc:
                detail = (
                    str(exc)
                    if isinstance(exc, DocumentOcrError)
                    else type(exc).__name__
                )
                try:
                    results.append(self.store.fail(job, detail=detail, now=now))
                except DocumentOcrClaimLost:
                    continue
        return tuple(results)


class DocumentOcrService:
    """Authorization and snapshot rules for queueing/reading OCR jobs."""

    def __init__(
        self,
        store: _DocumentOcrStore,
        content_repository,
        authorization_policy,
        *,
        require_clean: bool = True,
    ) -> None:
        self.store = store
        self.content_repository = content_repository
        self.authorization_policy = authorization_policy
        self.require_clean = require_clean

    def request(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        version: int,
        context,
        actor_id: str,
        occurred_at: datetime,
    ) -> DocumentOcrJob:
        from .application.authorization import Permission

        self._check(context, tenant_id, project_id, Permission.PROJECT_WRITE)
        if actor_id != context.user_id:
            raise DocumentAuthorizationError("DOCUMENT_ACTOR_MISMATCH")
        content = self._content(tenant_id, project_id, document_id, version)
        if self.require_clean and content.scan_status != "clean":
            from .document_storage import DocumentContentQuarantined

            raise DocumentContentQuarantined("DOCUMENT_CONTENT_QUARANTINED")
        return self.store.request(
            DocumentOcrJob(
                tenant_id=tenant_id,
                project_id=project_id,
                document_id=document_id,
                version=content.version,
                storage_ref=content.storage_ref,
                content_hash=content.content_hash,
                content_type=content.content_type,
                byte_size=content.byte_size,
                original_filename=content.original_filename,
                requested_by=actor_id,
                requested_at=occurred_at,
                next_attempt_at=occurred_at,
            )
        )

    def read(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        version: int,
        context,
    ) -> DocumentOcrJob:
        from .application.authorization import Permission

        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        job = self.store.get(tenant_id, project_id, document_id, version)
        if job is None:
            raise DocumentOcrNotFound("DOCUMENT_OCR_NOT_FOUND")
        return job

    def list(
        self, *, tenant_id: str, project_id: str, document_id: str, context
    ) -> tuple[DocumentOcrJob, ...]:
        from .application.authorization import Permission

        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.list(tenant_id, project_id, document_id)

    def retry(
        self,
        *,
        tenant_id: str,
        project_id: str,
        document_id: str,
        version: int,
        context,
        occurred_at: datetime,
    ) -> DocumentOcrJob:
        from .application.authorization import Permission

        self._check(context, tenant_id, project_id, Permission.PROJECT_WRITE)
        return self.store.retry(tenant_id, project_id, document_id, version, occurred_at)

    def _content(self, tenant_id, project_id, document_id, version):
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise DocumentOcrError("INVALID_DOCUMENT_OCR_VERSION")
        content = self.content_repository.get(
            tenant_id, project_id, document_id, version
        )
        if content is None:
            raise DocumentOcrNotFound("DOCUMENT_CONTENT_NOT_FOUND")
        return content

    def _check(self, context, tenant_id, project_id, permission) -> None:
        if context.tenant_id != tenant_id or context.project_id != project_id:
            raise DocumentAuthorizationError("DOCUMENT_CROSS_SCOPE")
        if not context.user_id.strip():
            raise DocumentAuthorizationError("DOCUMENT_ACTOR_REQUIRED")
        if not self.authorization_policy.is_allowed(context, permission):
            raise DocumentAuthorizationError("DOCUMENT_PERMISSION_DENIED")

    @staticmethod
    def error_dto(exc: Exception) -> APIError:
        if isinstance(exc, DocumentOcrNotFound):
            return validation_error(str(exc) or "DOCUMENT_OCR_NOT_FOUND", str(exc))
        if isinstance(exc, DocumentOcrNotRetryable):
            return conflict_error(
                str(exc) or "DOCUMENT_OCR_NOT_RETRYABLE", str(exc)
            )
        if isinstance(exc, DocumentOcrClaimLost):
            return conflict_error(str(exc) or "DOCUMENT_OCR_CLAIM_LOST", str(exc))
        from .document_storage import DocumentContentQuarantined

        if isinstance(exc, DocumentContentQuarantined):
            return conflict_error(
                str(exc) or "DOCUMENT_CONTENT_QUARANTINED", str(exc)
            )
        if isinstance(exc, DocumentAuthorizationError):
            from .api_errors import authorization_error

            return authorization_error(str(exc), str(exc))
        if isinstance(exc, DocumentOcrError):
            return validation_error(str(exc) or type(exc).__name__, str(exc))
        if isinstance(exc, ValueError):
            return validation_error(str(exc) or type(exc).__name__, str(exc))
        return persistence_error(type(exc).__name__, str(exc))


__all__ = [
    "DEFAULT_OCR_LEASE_SECONDS",
    "DEFAULT_OCR_MAX_ATTEMPTS",
    "DEFAULT_OCR_MAX_CHARS",
    "DocumentOCRAdapter",
    "DocumentOCRAdapterError",
    "DocumentOcrClaimLost",
    "DocumentOcrEngine",
    "DocumentOcrError",
    "DocumentOcrJob",
    "DocumentOcrNotFound",
    "DocumentOcrNotRetryable",
    "DocumentOcrRepository",
    "DocumentOcrRunner",
    "DocumentOcrService",
    "OCR_STATUSES",
    "OCR_SUPPORTED_TEXT_TYPES",
    "OCRRequest",
    "OCRResult",
    "OcrExtraction",
    "OcrUnsupported",
    "PostgresDocumentOcrRepository",
    "ReferenceDocumentOCRAdapter",
    "ReferenceDocumentOcrEngine",
    "SQLiteDocumentOcrRepository",
]

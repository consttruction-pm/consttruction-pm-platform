"""Measure a CUBI knowledge database without mutating it.

Production inventory questions ("how many cards are published?", "which locales
are actually approved?", "is the source content still what we published?") must
be answered from the database rather than from a report somebody wrote earlier.
The tool opens SQLite read-only, so it never migrates or rewrites evidence, and
it can measure a PostgreSQL database through the same queries so the two stores
are compared with one definition of every count.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

LOCALES = ("fa", "en", "de", "zh-Hans", "ar", "fr", "ja", "ko")
LEGACY_LOCALES = ("ru",)
# Persisted Chinese codes that the current registry folds into one slot.
LOCALE_ALIASES = {
    "zh": "zh-Hans",
    "zh-cn": "zh-Hans",
    "zh-tw": "zh-Hans",
    "zh-hant": "zh-Hans",
    "zh-hk": "zh-Hans",
    "zh-mo": "zh-Hans",
}


def _canonical_stored_locale(value: str) -> str:
    return LOCALE_ALIASES.get(value.strip().replace("_", "-").lower(), value)


class _Row:
    """Name and position access so one SQL path serves both drivers."""

    def __init__(self, names: tuple[str, ...], values: tuple[object, ...]) -> None:
        self._names = names
        self._values = values

    def __getitem__(self, key: object) -> object:
        if isinstance(key, int):
            return self._values[key]
        return self._values[self._names.index(str(key))]


class _SqliteReader:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        self._connection.row_factory = sqlite3.Row

    def query(self, sql: str, parameters: tuple = ()) -> list[_Row]:
        cursor = self._connection.execute(sql, parameters)
        names = tuple(column[0] for column in cursor.description or ())
        return [_Row(names, tuple(row)) for row in cursor.fetchall()]

    def metadata(self) -> dict[str, object]:
        return {"engine": "sqlite", "path": str(self.path), "sha256": _sha256(self.path)}

    def close(self) -> None:
        self._connection.close()


class _PostgresReader:
    def __init__(self, dsn: str) -> None:
        import psycopg
        from psycopg.rows import tuple_row

        self.dsn = dsn
        self._connection = psycopg.connect(dsn, autocommit=False, options=None)
        self._tuple_row = tuple_row

    def query(self, sql: str, parameters: tuple = ()) -> list[_Row]:
        cursor = self._connection.cursor(row_factory=self._tuple_row)
        cursor.execute(sql.replace("?", "%s"), tuple(parameters))
        names = tuple(column.name for column in cursor.description or ())
        return [_Row(names, tuple(row)) for row in cursor.fetchall()]

    def metadata(self) -> dict[str, object]:
        # A DSN may carry a password, so only the database identity is reported.
        database = self.query("SELECT current_database() AS name")[0]["name"]
        server = self.query("SHOW server_version")[0][0]
        return {"engine": "postgres", "database": database, "server_version": server}

    def close(self) -> None:
        self._connection.close()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _counts(reader: _SqliteReader | _PostgresReader, sql: str, parameters: tuple = ()) -> dict[str, int]:
    return {str(row[0]): int(row[1]) for row in reader.query(sql, parameters)}


def measure_reader(reader: _SqliteReader | _PostgresReader) -> dict[str, object]:
    cards = _counts(
        reader, "SELECT publication_status, COUNT(*) FROM knowledge_card GROUP BY 1"
    )
    validation = _counts(
        reader, "SELECT validation_status, COUNT(*) FROM knowledge_card GROUP BY 1"
    )
    card_types = _counts(
        reader, "SELECT card_type, COUNT(*) FROM knowledge_card GROUP BY 1"
    )
    total_cards = sum(cards.values())
    topics = _counts(
        reader,
        "SELECT source_id || ':' || status, COUNT(*) FROM knowledge_topic GROUP BY 1",
    )
    merged = int(
        reader.query(
            "SELECT COUNT(*) FROM knowledge_audit WHERE action='topic_merged'"
        )[0][0]
    )
    schema_row = reader.query("SELECT MAX(version) FROM knowledge_schema_migration")
    card_hashes = {
        str(row["card_id"]): row["content_hash"]
        for row in reader.query("SELECT card_id, content_hash FROM knowledge_card")
    }
    rows = reader.query(
        "SELECT card_id, locale, translation_status, review_status, machine_translated, "
        "localization_metadata_json, translation_version FROM knowledge_card_translation"
    )

    matrix: dict[str, dict[str, int]] = {locale: {} for locale in LOCALES}
    legacy_matrix: dict[str, dict[str, int]] = {locale: {} for locale in LEGACY_LOCALES}
    storage_codes: dict[str, int] = {}
    machine = 0
    stale = 0
    bound_rows = 0
    normalized_legacy = 0
    # One card has at most one row per product slot. When both a legacy and a
    # canonical Chinese code exist, keep the canonical row rather than counting
    # the same slot twice.
    per_card: dict[tuple[str, str], tuple[str, str]] = {}
    for row in rows:
        stored = str(row["locale"])
        canonical = _canonical_stored_locale(stored)
        storage_codes[stored] = storage_codes.get(stored, 0) + 1
        if canonical != stored:
            normalized_legacy += 1
        status = str(row["translation_status"])
        if canonical in matrix:
            key = (str(row["card_id"]), canonical)
            current = per_card.get(key)
            rank = {"published": 6, "approved": 5, "translated": 4, "review_required": 3, "draft": 2, "retired": 1, "missing": 0}
            if current is None or (rank.get(status, 0), stored == canonical) > (
                rank.get(current[0], 0),
                current[1] == canonical,
            ):
                per_card[key] = (status, stored)
        elif canonical in legacy_matrix:
            bucket = legacy_matrix[canonical]
            bucket[status] = bucket.get(status, 0) + 1
        if int(row["machine_translated"]):
            machine += 1
        metadata = json.loads(row["localization_metadata_json"] or "{}")
        bound_hash = metadata.get("source_card_hash")
        if bound_hash is not None:
            bound_rows += 1
            if bound_hash != card_hashes.get(str(row["card_id"])):
                stale += 1
    for (card_id, locale), (status, _stored) in per_card.items():
        bucket = matrix[locale]
        bucket[status] = bucket.get(status, 0) + 1
    approved = sum(
        value for bucket in matrix.values() for key, value in bucket.items() if key == "approved"
    )
    published_translations = sum(
        value for bucket in matrix.values() for key, value in bucket.items() if key == "published"
    )
    rejected = sum(
        value for bucket in matrix.values() for key, value in bucket.items() if key == "review_required"
    )
    slots = total_cards * (len(LOCALES) - 1)
    filled = sum(
        1
        for status, _stored in per_card.values()
        if status not in {"missing", "retired"}
    )
    legacy_records = sum(sum(bucket.values()) for bucket in legacy_matrix.values())
    return {
        "database": {
            **reader.metadata(),
            "schema_version": None
            if schema_row[0][0] is None
            else int(schema_row[0][0]),
        },
        "cards": {
            "total": total_cards,
            "published": cards.get("published", 0),
            "validated": validation.get("validated", 0),
            "draft": cards.get("draft", 0),
            "rejected": cards.get("rejected", 0),
            "retired": cards.get("retired", 0),
            "by_publication_status": cards,
            "by_validation_status": validation,
            "by_type": card_types,
        },
        "sources": {
            "topic_counts": topics,
            "topics_total": sum(topics.values()),
            "merged_duplicates": merged,
        },
        "translations": {
            "locales": list(LOCALES),
            "legacy_locales": list(LEGACY_LOCALES),
            "source_language": "en",
            "records": len(rows),
            "cards_with_translations": len({str(row["card_id"]) for row in rows}),
            "by_locale": matrix,
            "legacy_by_locale": legacy_matrix,
            "legacy_records": legacy_records,
            "normalized_legacy_records": normalized_legacy,
            "stored_locale_codes": storage_codes,
            "approved": approved,
            "published": published_translations,
            "review_required_or_rejected": rejected,
            "machine_generated": machine,
            "source_bound": bound_rows,
            "stale_source_bound": stale,
            "available_slots": slots,
            "filled_slots": filled,
            "missing_slots": slots - filled,
        },
    }


def measure(path: Path) -> dict[str, object]:
    reader = _SqliteReader(path)
    try:
        return measure_reader(reader)
    finally:
        reader.close()


def measure_postgres(dsn: str) -> dict[str, object]:
    reader = _PostgresReader(dsn)
    try:
        return measure_reader(reader)
    finally:
        reader.close()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("database", type=Path, nargs="?", default=None)
    target.add_argument("--dsn", help="Measure a PostgreSQL database instead of a file")
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args(argv)
    report = (
        measure_postgres(arguments.dsn)
        if arguments.dsn
        else measure(arguments.database)
    )
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if arguments.output is None:
        print(payload)
    else:
        arguments.output.write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

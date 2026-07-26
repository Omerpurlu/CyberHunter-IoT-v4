"""Safely copy the two application tables from SQLite to PostgreSQL.

The default mode is a read-only dry run.  Data is written only with --apply.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from psycopg import sql


BASE_DIR = Path(__file__).resolve().parent
SQLITE_PATH = BASE_DIR / "CyberHunter.db"
ENV_PATH = BASE_DIR / ".env"
EXPECTED_REVISION = "6b9850c2d44d"

TABLES: dict[str, tuple[str, ...]] = {
    "LedLoglari": (
        "id",
        "device_id",
        "led",
        "sequence",
        "device_timestamp",
        "nonce",
        "server_received_at",
        "message",
        "encryption_version",
    ),
    "CihazEmirleri": (
        "id",
        "device_id",
        "komut",
        "durum",
        "olusturulma_zamani",
        "message",
        "encryption_version",
    ),
}


class MigrationError(RuntimeError):
    """A controlled migration failure safe to show to an operator."""


def quote_sqlite_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def sqlite_connection() -> sqlite3.Connection:
    if not SQLITE_PATH.is_file():
        raise MigrationError(f"SQLite dosyasi bulunamadi: {SQLITE_PATH}")

    uri = f"{SQLITE_PATH.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.execute("PRAGMA query_only = ON")
    if connection.execute("PRAGMA query_only").fetchone() != (1,):
        connection.close()
        raise MigrationError("SQLite baglantisinin read-only oldugu dogrulanamadi.")

    # URI mode=ro must reject a write to the main database. No change is made.
    try:
        connection.execute("CREATE TABLE __migration_readonly_probe (id INTEGER)")
    except sqlite3.OperationalError as exc:
        if "readonly" not in str(exc).lower():
            connection.close()
            raise MigrationError(
                "SQLite read-only kontrolu beklenmeyen bir hata verdi."
            ) from exc
    else:
        connection.execute("DROP TABLE __migration_readonly_probe")
        connection.close()
        raise MigrationError("SQLite baglantisi yazmaya izin veriyor; islem durduruldu.")

    return connection


def postgres_parameters() -> dict[str, Any]:
    load_dotenv(dotenv_path=ENV_PATH, override=False)
    names = (
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    )
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise MigrationError(
            "Eksik PostgreSQL ortam degiskenleri: " + ", ".join(missing)
        )
    try:
        port = int(os.environ["POSTGRES_PORT"])
    except ValueError as exc:
        raise MigrationError("POSTGRES_PORT gecerli bir tamsayi degil.") from exc
    return {
        "host": os.environ["POSTGRES_HOST"],
        "port": port,
        "dbname": os.environ["POSTGRES_DB"],
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
    }


def verify_sqlite(
    connection: sqlite3.Connection,
) -> tuple[dict[str, int], dict[str, list[tuple[Any, ...]]]]:
    integrity = connection.execute("PRAGMA integrity_check").fetchone()
    if integrity != ("ok",):
        raise MigrationError("SQLite integrity_check sonucu 'ok' degil.")
    print("SQLite integrity_check: ok")

    existing = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    counts: dict[str, int] = {}
    rows: dict[str, list[tuple[Any, ...]]] = {}
    for table, columns in TABLES.items():
        if table not in existing:
            raise MigrationError(f"SQLite kaynak tablosu bulunamadi: {table}")
        source_columns = {
            row[1]
            for row in connection.execute(
                f"PRAGMA table_info({quote_sqlite_identifier(table)})"
            )
        }
        missing = set(columns) - source_columns
        if missing:
            raise MigrationError(
                f"SQLite {table} tablosunda eksik sutunlar: {', '.join(sorted(missing))}"
            )
        selected = ", ".join(quote_sqlite_identifier(c) for c in columns)
        table_rows = connection.execute(
            f"SELECT {selected} FROM {quote_sqlite_identifier(table)} "
            f"ORDER BY {quote_sqlite_identifier('id')}"
        ).fetchall()
        counts[table] = len(table_rows)
        rows[table] = table_rows
        print(f"SQLite {table}: {counts[table]} kayit; sutunlar uygun")
    return counts, rows


def verify_postgres_schema(
    connection: psycopg.Connection[Any],
) -> dict[str, int]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT version_num FROM alembic_version")
        revisions = [row[0] for row in cursor.fetchall()]
        if revisions != [EXPECTED_REVISION]:
            raise MigrationError(
                "Alembic revision beklenen degerde degil "
                f"(beklenen: {EXPECTED_REVISION})."
            )
        print(f"Alembic revision: {EXPECTED_REVISION} (uygun)")

        cursor.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = ANY(%s)
            """,
            (list(TABLES),),
        )
        found: dict[str, set[str]] = {table: set() for table in TABLES}
        for table, column in cursor.fetchall():
            found[table].add(column)

        counts: dict[str, int] = {}
        for table, columns in TABLES.items():
            if not found[table]:
                raise MigrationError(f"PostgreSQL hedef tablosu bulunamadi: {table}")
            missing = set(columns) - found[table]
            if missing:
                raise MigrationError(
                    f"PostgreSQL {table} tablosunda eksik sutunlar: "
                    + ", ".join(sorted(missing))
                )
            cursor.execute(
                sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table))
            )
            counts[table] = cursor.fetchone()[0]
            print(f"PostgreSQL {table}: {counts[table]} kayit; sutunlar uygun")
        return counts


def ensure_empty(counts: dict[str, int]) -> None:
    nonempty = [f"{table} ({count})" for table, count in counts.items() if count]
    if nonempty:
        raise MigrationError(
            "Hedef tablolar bos degil; aktarim yapilmadi: " + ", ".join(nonempty)
        )


def check_primary_key_conflicts(
    connection: psycopg.Connection[Any],
    source_rows: dict[str, list[tuple[Any, ...]]],
) -> None:
    with connection.cursor() as cursor:
        for table, rows in source_rows.items():
            ids = [row[0] for row in rows]
            if not ids:
                print(f"{table}: primary key cakismasi yok (kaynak bos)")
                continue
            cursor.execute(
                sql.SQL("SELECT id FROM {} WHERE id = ANY(%s) ORDER BY id").format(
                    sql.Identifier(table)
                ),
                (ids,),
            )
            conflicts = cursor.fetchall()
            if conflicts:
                raise MigrationError(
                    f"{table}: {len(conflicts)} primary key cakismasi bulundu."
                )
            print(f"{table}: primary key cakismasi yok")


def run_dry_run(
    parameters: dict[str, Any],
    source_counts: dict[str, int],
    source_rows: dict[str, list[tuple[Any, ...]]],
) -> None:
    with psycopg.connect(**parameters) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        before = verify_postgres_schema(connection)
        ensure_empty(before)
        check_primary_key_conflicts(connection, source_rows)
        for table in TABLES:
            print(f"{table}: tasinacak kayit sayisi {source_counts[table]}")
        connection.rollback()

    # A new connection proves the read-only dry run left counts unchanged.
    with psycopg.connect(**parameters) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        after = verify_postgres_schema(connection)
        connection.rollback()
    if after != before:
        raise MigrationError("Dry-run sirasinda PostgreSQL kayit sayilari degisti.")
    print("Dry-run tamamlandi; INSERT calistirilmadi.")
    print("PostgreSQL kayit sayilari degismedi ve hedef tablolar hala bos.")


def insert_rows(
    cursor: psycopg.Cursor[Any],
    table: str,
    columns: tuple[str, ...],
    rows: list[tuple[Any, ...]],
) -> None:
    if not rows:
        return
    statement = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )
    cursor.executemany(statement, rows)


def verify_exact_rows(
    cursor: psycopg.Cursor[Any],
    source_rows: dict[str, list[tuple[Any, ...]]],
) -> None:
    for table, columns in TABLES.items():
        statement = sql.SQL("SELECT {} FROM {} ORDER BY {}").format(
            sql.SQL(", ").join(map(sql.Identifier, columns)),
            sql.Identifier(table),
            sql.Identifier("id"),
        )
        cursor.execute(statement)
        target_rows = cursor.fetchall()
        if target_rows != source_rows[table]:
            raise MigrationError(
                f"{table}: kaynak ve hedef satirlari birebir eslesmiyor."
            )
        print(f"{table}: {len(target_rows)} satir birebir dogrulandi")


def set_id_sequence(cursor: psycopg.Cursor[Any], table: str) -> None:
    relation = f'"{table}"'
    cursor.execute("SELECT pg_get_serial_sequence(%s, %s)", (relation, "id"))
    sequence_name = cursor.fetchone()[0]
    if not sequence_name:
        raise MigrationError(f"{table}: id sequence bulunamadi.")
    cursor.execute(
        sql.SQL("SELECT MAX({}) FROM {}").format(
            sql.Identifier("id"), sql.Identifier(table)
        )
    )
    maximum = cursor.fetchone()[0]
    if maximum is None:
        cursor.execute("SELECT setval(%s::regclass, 1, false)", (sequence_name,))
    else:
        cursor.execute(
            "SELECT setval(%s::regclass, %s, true)", (sequence_name, maximum)
        )
    print(f"{table}: id sequence MAX(id) sonrasina ayarlandi")


def run_apply(
    parameters: dict[str, Any],
    source_counts: dict[str, int],
    source_rows: dict[str, list[tuple[Any, ...]]],
) -> None:
    with psycopg.connect(**parameters) as connection:
        try:
            counts = verify_postgres_schema(connection)
            ensure_empty(counts)
            check_primary_key_conflicts(connection, source_rows)
            with connection.cursor() as cursor:
                for table in ("LedLoglari", "CihazEmirleri"):
                    insert_rows(cursor, table, TABLES[table], source_rows[table])

                for table, expected in source_counts.items():
                    cursor.execute(
                        sql.SQL("SELECT COUNT(*) FROM {}").format(
                            sql.Identifier(table)
                        )
                    )
                    actual = cursor.fetchone()[0]
                    if actual != expected:
                        raise MigrationError(
                            f"{table}: kayit sayisi uyusmuyor "
                            f"(kaynak={expected}, hedef={actual})."
                        )

                verify_exact_rows(cursor, source_rows)
                for table in TABLES:
                    set_id_sequence(cursor, table)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    print("VERI TASIMA BASARILI")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "CyberHunter SQLite verilerini PostgreSQL'e guvenli bicimde tasir. "
            "Varsayilan mod dry-run'dir."
        )
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Kontrolleri yapar, PostgreSQL'e veri yazmaz (varsayilan).",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Dogrulamalardan sonra verileri tek transaction ile tasir.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sqlite_db: sqlite3.Connection | None = None
    try:
        print(f"SQLite kaynak: {SQLITE_PATH}")
        sqlite_db = sqlite_connection()
        source_counts, source_rows = verify_sqlite(sqlite_db)
        parameters = postgres_parameters()
        if args.apply:
            run_apply(parameters, source_counts, source_rows)
        else:
            run_dry_run(parameters, source_counts, source_rows)
        return 0
    except Exception as exc:
        # Never expose connection strings, passwords, or row/token contents.
        if isinstance(exc, MigrationError):
            message = str(exc)
        else:
            message = f"{type(exc).__name__}; ayrintilar guvenlik icin gizlendi"
        print(f"HATA: {message}", file=sys.stderr)
        return 1
    finally:
        if sqlite_db is not None:
            sqlite_db.close()


if __name__ == "__main__":
    raise SystemExit(main())

"""The migration runner: order, applied once, edited files refused. Uses versions 9001+ and temp tables only."""

from pathlib import Path

import pytest

from app.core.db import connect
from app.core.migrations import MIGRATIONS_DIR, MigrationError, discover, migrate


def test_repository_migrations_are_numbered_in_order():
    versions = [m.version for m in discover(MIGRATIONS_DIR)]
    assert versions == list(range(1, len(versions) + 1))


def test_bad_file_name_is_refused(tmp_path: Path):
    (tmp_path / "add_table.sql").write_text("SELECT 1")
    with pytest.raises(MigrationError):
        discover(tmp_path)


def test_applies_once_and_refuses_edited_files(tmp_path: Path):
    (tmp_path / "9001_first.sql").write_text("CREATE TEMP TABLE t_migrate_a (id int);")
    (tmp_path / "9002_second.sql").write_text("INSERT INTO t_migrate_a VALUES (1);")
    with connect() as conn:
        try:
            assert [m.label for m in migrate(conn, dry_run=True, directory=tmp_path)] == ["9001_first", "9002_second"]
            assert [m.label for m in migrate(conn, directory=tmp_path)] == ["9001_first", "9002_second"]
            assert conn.execute("SELECT count(*) FROM t_migrate_a").fetchone()[0] == 1
            assert migrate(conn, directory=tmp_path) == []  # nothing left to do

            (tmp_path / "9002_second.sql").write_text("INSERT INTO t_migrate_a VALUES (2);")
            with pytest.raises(MigrationError, match="changed after it was applied"):
                migrate(conn, directory=tmp_path)

            (tmp_path / "9002_second.sql").write_text("INSERT INTO t_migrate_a VALUES (1);")
            (tmp_path / "9003_broken.sql").write_text("INSERT INTO t_migrate_a VALUES ('not a number');")
            with pytest.raises(Exception):  # noqa: B017 - any database error
                migrate(conn, directory=tmp_path)
            recorded = conn.execute("SELECT version FROM public.schema_migrations WHERE version > 9000").fetchall()
            assert recorded == [(9001,), (9002,)]  # the failed file rolled back with its row
        finally:
            conn.execute("DELETE FROM public.schema_migrations WHERE version > 9000")


def test_up_to_holds_back_later_files(tmp_path: Path):
    (tmp_path / "9001_first.sql").write_text("CREATE TEMP TABLE t_migrate_b (id int);")
    (tmp_path / "9002_destructive.sql").write_text("DROP TABLE t_migrate_b;")
    with connect() as conn:
        try:
            assert [m.label for m in migrate(conn, directory=tmp_path, up_to=9001)] == ["9001_first"]
            assert conn.execute("SELECT to_regclass('pg_temp.t_migrate_b') IS NOT NULL").fetchone()[0]
            assert [m.label for m in migrate(conn, directory=tmp_path)] == ["9002_destructive"]  # runs once asked for
        finally:
            conn.execute("DELETE FROM public.schema_migrations WHERE version > 9000")

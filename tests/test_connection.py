"""
Copyright © 2026 by BGEO. All rights reserved.
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.

Connection tests.
"""
# -*- coding: utf-8 -*-
import pytest


class TestConnectionImports:
    """Test connection module imports."""

    def test_import_connection_functions(self):
        from hydraulic_engine import (
            create_pg_connection,
            create_gpkg_connection,
            create_sqlite_connection,
            get_connection,
            close_connection,
        )
        assert create_pg_connection is not None
        assert create_gpkg_connection is not None
        assert create_sqlite_connection is not None
        assert get_connection is not None
        assert close_connection is not None

    def test_import_dao_classes(self):
        from hydraulic_engine.utils.tools_db import (
            HeDbDao,
            HePgDao,
            HeSqliteDao,
            HeGpkgDao,
            DbType,
        )
        assert HeDbDao is not None
        assert HePgDao is not None
        assert HeSqliteDao is not None
        assert HeGpkgDao is not None
        assert DbType is not None


class TestSqliteConnection:
    """Test SQLite connection functionality."""

    def test_create_sqlite_connection(self, tmp_path):
        from hydraulic_engine import create_sqlite_connection, get_connection, close_connection

        db_path = str(tmp_path / "test.db")
        dao = create_sqlite_connection(db_path, set_as_default=True)
        assert dao is not None
        assert dao.is_connected()
        assert get_connection() is dao
        close_connection()
        assert get_connection() is None

    def test_sqlite_execute_and_query(self, tmp_path):
        from hydraulic_engine import create_sqlite_connection, close_connection

        db_path = str(tmp_path / "test.db")
        dao = create_sqlite_connection(db_path)

        dao.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        dao.execute("INSERT INTO test (name) VALUES (?)", ("test_value",))

        row = dao.get_row("SELECT * FROM test WHERE name = ?", ("test_value",))
        assert row is not None
        assert row[1] == "test_value"

        dao.execute("INSERT INTO test (name) VALUES (?)", ("test_value_2",))
        rows = dao.get_rows("SELECT * FROM test")
        assert len(rows) == 2

        close_connection()

    def test_sqlite_connect_failure_raises(self):
        from hydraulic_engine.utils.tools_db import HeSqliteDao, DatabaseError

        dao = HeSqliteDao()
        with pytest.raises(DatabaseError):
            dao.connect("/invalid/path/test.db")


class TestGpkgConnection:
    """Test GeoPackage connection functionality."""

    def test_create_gpkg_connection(self, tmp_path):
        from hydraulic_engine import create_gpkg_connection, get_connection, close_connection

        gpkg_path = str(tmp_path / "test.gpkg")
        dao = create_gpkg_connection(gpkg_path, set_as_default=True)
        assert dao is not None
        assert dao.is_connected()
        assert get_connection() is dao
        close_connection()
        assert get_connection() is None

    def test_gpkg_get_tables_empty(self, tmp_path):
        from hydraulic_engine import create_gpkg_connection, close_connection

        gpkg_path = str(tmp_path / "test.gpkg")
        dao = create_gpkg_connection(gpkg_path, set_as_default=False)
        tables = dao.get_tables()
        assert tables == []
        dao.close_db()
        close_connection()

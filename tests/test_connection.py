"""
Copyright © 2026 by BGEO. All rights reserved.
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.

Connection tests.
"""
# -*- coding: utf-8 -*-
import os
import tempfile
import pytest


class TestConnectionImports:
    """Test connection module imports."""

    def test_import_connection_functions(self):
        """Test that connection functions can be imported from package."""
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
        """Test that DAO classes can be imported."""
        from hydraulic_engine.lib.tools_db import (
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
        """Test creating a SQLite connection."""
        from hydraulic_engine import create_sqlite_connection, get_connection, close_connection

        db_path = str(tmp_path / "test.db")

        # Create connection
        dao = create_sqlite_connection(db_path, set_as_default=True)
        assert dao is not None
        assert dao.is_connected()

        # Check it's set as default
        assert get_connection() is dao

        # Close connection
        close_connection()
        assert get_connection() is None

    def test_sqlite_execute_and_query(self, tmp_path):
        """Test SQLite execute and query operations."""
        from hydraulic_engine import create_sqlite_connection, close_connection

        db_path = str(tmp_path / "test.db")
        dao = create_sqlite_connection(db_path)

        # Create table
        assert dao.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")

        # Insert data
        assert dao.execute("INSERT INTO test (name) VALUES (?)", ("test_value",))

        # Query data
        row = dao.get_row("SELECT * FROM test WHERE name = ?", ("test_value",))
        assert row is not None
        assert row[1] == "test_value"

        # Query multiple rows
        dao.execute("INSERT INTO test (name) VALUES (?)", ("test_value_2",))
        rows = dao.get_rows("SELECT * FROM test")
        assert rows is not None
        assert len(rows) == 2

        close_connection()


class TestGpkgConnection:
    """Test GeoPackage connection functionality."""

    def test_create_gpkg_connection(self, tmp_path):
        """Test creating a GeoPackage connection."""
        from hydraulic_engine import create_gpkg_connection, get_connection, close_connection

        gpkg_path = str(tmp_path / "test.gpkg")

        # Create connection (this will create the file)
        dao = create_gpkg_connection(gpkg_path, set_as_default=True)
        assert dao is not None
        assert dao.is_connected()

        # Check it's set as default
        assert get_connection() is dao

        # Close connection
        close_connection()
        assert get_connection() is None

    def test_gpkg_clone(self, tmp_path):
        """Test GeoPackage DAO cloning."""
        from hydraulic_engine import create_gpkg_connection, close_connection

        gpkg_path = str(tmp_path / "test.gpkg")
        dao = create_gpkg_connection(gpkg_path, set_as_default=False)

        # Clone the DAO
        cloned_dao = dao.clone()
        assert cloned_dao is not None
        assert cloned_dao.is_connected()
        assert cloned_dao is not dao

        dao.close_db()
        cloned_dao.close_db()


class TestPgConnection:
    """Test PostgreSQL connection functionality (requires running PostgreSQL)."""

    @pytest.mark.skip(reason="Requires running PostgreSQL server")
    def test_create_pg_connection(self):
        """Test creating a PostgreSQL connection."""
        from hydraulic_engine import create_pg_connection, get_connection, close_connection

        # This test requires a running PostgreSQL server
        dao = create_pg_connection(
            host="localhost",
            port=5432,
            dbname="test_db",
            user="test_user",
            password="test_password",
            set_as_default=True
        )
        assert dao is not None
        assert dao.is_connected()

        # Check it's set as default
        assert get_connection() is dao

        # Close connection
        close_connection()
        assert get_connection() is None


class TestConnectionWithActions:
    """Test that actions use the global connection."""

    def test_action_uses_global_connection(self, tmp_path):
        """Test that actions automatically use the global connection."""
        from hydraulic_engine import create_sqlite_connection, get_connection, close_connection
        from hydraulic_engine.core.actions import ImportRpt, ExportInp

        db_path = str(tmp_path / "test.db")
        dao = create_sqlite_connection(db_path, set_as_default=True)

        # Create actions without passing DAO
        import_action = ImportRpt()
        export_action = ExportInp()

        # They should use the global connection
        assert import_action.dao is dao
        assert export_action.dao is dao

        close_connection()

    def test_action_uses_explicit_connection(self, tmp_path):
        """Test that actions can use an explicit connection."""
        from hydraulic_engine import create_sqlite_connection, close_connection
        from hydraulic_engine.core.actions import ImportRpt

        db_path1 = str(tmp_path / "test1.db")
        db_path2 = str(tmp_path / "test2.db")

        # Create global connection
        global_dao = create_sqlite_connection(db_path1, set_as_default=True)

        # Create explicit connection
        from hydraulic_engine.lib.tools_db import HeSqliteDao
        explicit_dao = HeSqliteDao()
        explicit_dao.connect(db_path2)

        # Create action with explicit DAO
        import_action = ImportRpt(dao=explicit_dao)

        # It should use the explicit connection, not global
        assert import_action.dao is explicit_dao
        assert import_action.dao is not global_dao

        explicit_dao.close_db()
        close_connection()

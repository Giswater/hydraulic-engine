"""
This file is part of Hydraulic Engine
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
import sqlite3
from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod
from enum import Enum

try:
    import psycopg
    from psycopg.rows import dict_row, tuple_row
    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False

from . import tools_log


class DbType(Enum):
    """Database type enumeration"""
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    GEOPACKAGE = "geopackage"


class HeDbDao(ABC):
    """
    Abstract base class for Database Access Object.
    Provides interface for database operations.
    """

    def __init__(self):
        self.conn = None
        self.cursor = None
        self.last_error: Optional[str] = None
        self.db_type: Optional[DbType] = None

    @abstractmethod
    def connect(self, **kwargs) -> bool:
        """
        Connect to the database.

        :param kwargs: Connection parameters
        :return: True if connection successful
        """
        pass

    @abstractmethod
    def close_db(self) -> None:
        """Close the database connection."""
        pass

    @abstractmethod
    def execute(self, sql: str, params: Optional[tuple] = None, commit: bool = True) -> bool:
        """
        Execute a SQL statement.

        :param sql: SQL statement
        :param params: Query parameters
        :param commit: Whether to commit after execution
        :return: True if execution successful
        """
        pass

    @abstractmethod
    def get_rows(self, sql: str, params: Optional[tuple] = None) -> Optional[List[tuple]]:
        """
        Execute a query and return all rows.

        :param sql: SQL query
        :param params: Query parameters
        :return: List of rows or None
        """
        pass

    @abstractmethod
    def get_row(self, sql: str, params: Optional[tuple] = None) -> Optional[tuple]:
        """
        Execute a query and return first row.

        :param sql: SQL query
        :param params: Query parameters
        :return: First row or None
        """
        pass

    def commit(self) -> bool:
        """
        Commit the current transaction.

        :return: True if commit successful
        """
        try:
            if self.conn:
                self.conn.commit()
                return True
        except Exception as e:
            self.last_error = str(e)
            tools_log.log_error(f"Commit error: {e}")
        return False

    def rollback(self) -> None:
        """Rollback the current transaction."""
        try:
            if self.conn:
                self.conn.rollback()
        except Exception as e:
            self.last_error = str(e)
            tools_log.log_error(f"Rollback error: {e}")

    def is_connected(self) -> bool:
        """
        Check if database is connected.

        :return: True if connected
        """
        return self.conn is not None

    @abstractmethod
    def clone(self) -> "HeDbDao":
        """
        Create a clone of this DAO with a new connection.

        :return: New DAO instance
        """
        pass


class HePgDao(HeDbDao):
    """
    PostgreSQL Database Access Object using psycopg3.
    """

    def __init__(self):
        super().__init__()
        self.db_type = DbType.POSTGRESQL
        self._connection_params: Dict[str, Any] = {}

    def connect(
        self,
        host: str = "localhost",
        port: int = 5432,
        dbname: str = "",
        user: str = "",
        password: str = "",
        schema: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Connect to PostgreSQL database using psycopg3.

        :param host: Database host
        :param port: Database port
        :param dbname: Database name
        :param user: Username
        :param password: Password
        :param schema: Default schema (optional)
        :return: True if connection successful
        """
        if not PSYCOPG_AVAILABLE:
            self.last_error = "psycopg3 is not installed. Install with: pip install psycopg[binary]"
            tools_log.log_error(self.last_error)
            return False

        try:
            # Store connection params for cloning
            self._connection_params = {
                "host": host,
                "port": port,
                "dbname": dbname,
                "user": user,
                "password": password,
                "schema": schema,
                **kwargs
            }

            # Build connection string
            conninfo = f"host={host} port={port} dbname={dbname} user={user} password={password}"

            # Add any additional parameters
            for key, value in kwargs.items():
                if key not in ("host", "port", "dbname", "user", "password", "schema"):
                    conninfo += f" {key}={value}"

            self.conn = psycopg.connect(conninfo, autocommit=False)
            self.cursor = self.conn.cursor()

            # Set search_path if schema is provided
            if schema:
                self.execute(f"SET search_path TO {schema}, public", commit=False)

            tools_log.log_info(f"Connected to PostgreSQL database: {dbname}@{host}:{port}")
            return True

        except Exception as e:
            self.last_error = str(e)
            tools_log.log_error(f"PostgreSQL connection error: {e}")
            return False

    def close_db(self) -> None:
        """Close the database connection."""
        try:
            if self.cursor:
                self.cursor.close()
                self.cursor = None
            if self.conn:
                self.conn.close()
                self.conn = None
            tools_log.log_info("PostgreSQL connection closed")
        except Exception as e:
            self.last_error = str(e)
            tools_log.log_error(f"Error closing PostgreSQL connection: {e}")

    def execute(self, sql: str, params: Optional[tuple] = None, commit: bool = True) -> bool:
        """
        Execute a SQL statement.

        :param sql: SQL statement
        :param params: Query parameters
        :param commit: Whether to commit after execution
        :return: True if execution successful
        """
        try:
            if not self.conn or not self.cursor:
                self.last_error = "Not connected to database"
                return False

            if params:
                self.cursor.execute(sql, params)
            else:
                self.cursor.execute(sql)

            if commit:
                self.conn.commit()

            return True

        except Exception as e:
            self.last_error = str(e)
            tools_log.log_error(f"Execute error: {e}\nSQL: {sql}")
            self.rollback()
            return False

    def get_rows(self, sql: str, params: Optional[tuple] = None) -> Optional[List[tuple]]:
        """
        Execute a query and return all rows.

        :param sql: SQL query
        :param params: Query parameters
        :return: List of rows or None
        """
        try:
            if not self.conn or not self.cursor:
                self.last_error = "Not connected to database"
                return None

            if params:
                self.cursor.execute(sql, params)
            else:
                self.cursor.execute(sql)

            return self.cursor.fetchall()

        except Exception as e:
            self.last_error = str(e)
            tools_log.log_error(f"Query error: {e}\nSQL: {sql}")
            return None

    def get_row(self, sql: str, params: Optional[tuple] = None) -> Optional[tuple]:
        """
        Execute a query and return first row.

        :param sql: SQL query
        :param params: Query parameters
        :return: First row or None
        """
        try:
            if not self.conn or not self.cursor:
                self.last_error = "Not connected to database"
                return None

            if params:
                self.cursor.execute(sql, params)
            else:
                self.cursor.execute(sql)

            return self.cursor.fetchone()

        except Exception as e:
            self.last_error = str(e)
            tools_log.log_error(f"Query error: {e}\nSQL: {sql}")
            return None

    def get_rows_dict(self, sql: str, params: Optional[tuple] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a query and return all rows as dictionaries.

        :param sql: SQL query
        :param params: Query parameters
        :return: List of dictionaries or None
        """
        try:
            if not self.conn:
                self.last_error = "Not connected to database"
                return None

            with self.conn.cursor(row_factory=dict_row) as cur:
                if params:
                    cur.execute(sql, params)
                else:
                    cur.execute(sql)
                return cur.fetchall()

        except Exception as e:
            self.last_error = str(e)
            tools_log.log_error(f"Query error: {e}\nSQL: {sql}")
            return None

    def clone(self) -> "HePgDao":
        """
        Create a clone of this DAO with a new connection.

        :return: New DAO instance with same connection parameters
        """
        new_dao = HePgDao()
        if self._connection_params:
            new_dao.connect(**self._connection_params)
        return new_dao

    def get_aux_conn(self) -> Optional["HePgDao"]:
        """
        Get an auxiliary connection for parallel operations.

        :return: New DAO instance
        """
        return self.clone()


class HeSqliteDao(HeDbDao):
    """
    SQLite Database Access Object.
    """

    def __init__(self):
        super().__init__()
        self.db_type = DbType.SQLITE
        self.db_path: Optional[str] = None

    def connect(self, db_path: str, **kwargs) -> bool:
        """
        Connect to SQLite database.

        :param db_path: Path to SQLite database file
        :return: True if connection successful
        """
        try:
            self.db_path = db_path
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()

            # Enable foreign keys
            self.cursor.execute("PRAGMA foreign_keys = ON")

            tools_log.log_info(f"Connected to SQLite database: {db_path}")
            return True

        except Exception as e:
            self.last_error = str(e)
            tools_log.log_error(f"SQLite connection error: {e}")
            return False

    def close_db(self) -> None:
        """Close the database connection."""
        try:
            if self.cursor:
                self.cursor.close()
                self.cursor = None
            if self.conn:
                self.conn.close()
                self.conn = None
            tools_log.log_info("SQLite connection closed")
        except Exception as e:
            self.last_error = str(e)
            tools_log.log_error(f"Error closing SQLite connection: {e}")

    def execute(self, sql: str, params: Optional[tuple] = None, commit: bool = True) -> bool:
        """
        Execute a SQL statement.

        :param sql: SQL statement
        :param params: Query parameters
        :param commit: Whether to commit after execution
        :return: True if execution successful
        """
        try:
            if not self.conn or not self.cursor:
                self.last_error = "Not connected to database"
                return False

            if params:
                self.cursor.execute(sql, params)
            else:
                self.cursor.execute(sql)

            if commit:
                self.conn.commit()

            return True

        except Exception as e:
            self.last_error = str(e)
            tools_log.log_error(f"Execute error: {e}\nSQL: {sql}")
            self.rollback()
            return False

    def get_rows(self, sql: str, params: Optional[tuple] = None) -> Optional[List[tuple]]:
        """
        Execute a query and return all rows.

        :param sql: SQL query
        :param params: Query parameters
        :return: List of rows or None
        """
        try:
            if not self.conn or not self.cursor:
                self.last_error = "Not connected to database"
                return None

            if params:
                self.cursor.execute(sql, params)
            else:
                self.cursor.execute(sql)

            return self.cursor.fetchall()

        except Exception as e:
            self.last_error = str(e)
            tools_log.log_error(f"Query error: {e}\nSQL: {sql}")
            return None

    def get_row(self, sql: str, params: Optional[tuple] = None) -> Optional[tuple]:
        """
        Execute a query and return first row.

        :param sql: SQL query
        :param params: Query parameters
        :return: First row or None
        """
        try:
            if not self.conn or not self.cursor:
                self.last_error = "Not connected to database"
                return None

            if params:
                self.cursor.execute(sql, params)
            else:
                self.cursor.execute(sql)

            return self.cursor.fetchone()

        except Exception as e:
            self.last_error = str(e)
            tools_log.log_error(f"Query error: {e}\nSQL: {sql}")
            return None

    def clone(self) -> "HeSqliteDao":
        """
        Create a clone of this DAO with a new connection.

        :return: New DAO instance
        """
        new_dao = HeSqliteDao()
        if self.db_path:
            new_dao.connect(self.db_path)
        return new_dao


class HeGpkgDao(HeSqliteDao):
    """
    GeoPackage Database Access Object.
    Extends SQLite DAO with GeoPackage specific functionality.
    """

    def __init__(self):
        super().__init__()
        self.db_type = DbType.GEOPACKAGE

    def connect(self, gpkg_path: str, **kwargs) -> bool:
        """
        Connect to GeoPackage database.

        :param gpkg_path: Path to GeoPackage file
        :return: True if connection successful
        """
        result = super().connect(gpkg_path, **kwargs)
        if result:
            # Load spatialite extension if available
            try:
                self.conn.enable_load_extension(True)
                # Try to load mod_spatialite (optional)
                # self.conn.load_extension("mod_spatialite")
            except Exception:
                # Spatialite not available, continue without it
                pass
            tools_log.log_info(f"Connected to GeoPackage: {gpkg_path}")
        return result

    def clone(self) -> "HeGpkgDao":
        """
        Create a clone of this DAO with a new connection.

        :return: New DAO instance
        """
        new_dao = HeGpkgDao()
        if self.db_path:
            new_dao.connect(self.db_path)
        return new_dao

    def get_tables(self) -> Optional[List[str]]:
        """
        Get list of tables in the GeoPackage.

        :return: List of table names or None
        """
        sql = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'gpkg_%' AND name NOT LIKE 'sqlite_%'"
        rows = self.get_rows(sql)
        if rows:
            return [row[0] for row in rows]
        return None

    def get_geometry_tables(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get list of geometry tables from gpkg_contents.

        :return: List of geometry table info or None
        """
        sql = """
            SELECT table_name, data_type, identifier, description, srs_id 
            FROM gpkg_contents 
            WHERE data_type IN ('features', 'tiles')
        """
        rows = self.get_rows(sql)
        if rows:
            return [
                {
                    "table_name": row[0],
                    "data_type": row[1],
                    "identifier": row[2],
                    "description": row[3],
                    "srs_id": row[4]
                }
                for row in rows
            ]
        return None


# =============================================================================
# Connection Factory and Global Connection Management
# =============================================================================

def create_pg_connection(
    host: str = "localhost",
    port: int = 5432,
    dbname: str = "",
    user: str = "",
    password: str = "",
    schema: Optional[str] = None,
    set_as_default: bool = True,
    **kwargs
) -> Optional[HePgDao]:
    """
    Create a PostgreSQL connection.

    :param host: Database host
    :param port: Database port
    :param dbname: Database name
    :param user: Username
    :param password: Password
    :param schema: Default schema (optional)
    :param set_as_default: Set this connection as the default global connection
    :return: HePgDao instance or None if connection failed
    """
    from ..config import config

    dao = HePgDao()
    if dao.connect(host=host, port=port, dbname=dbname, user=user, password=password, schema=schema, **kwargs):
        if set_as_default:
            # Close existing connection if any
            if config.session_vars.get('db_connection'):
                config.session_vars['db_connection'].close_db()
            config.session_vars['db_connection'] = dao
        return dao
    return None


def create_gpkg_connection(
    gpkg_path: str,
    set_as_default: bool = True,
    **kwargs
) -> Optional[HeGpkgDao]:
    """
    Create a GeoPackage connection.

    :param gpkg_path: Path to GeoPackage file
    :param set_as_default: Set this connection as the default global connection
    :return: HeGpkgDao instance or None if connection failed
    """
    from ..config import config

    dao = HeGpkgDao()
    if dao.connect(gpkg_path, **kwargs):
        if set_as_default:
            # Close existing connection if any
            if config.session_vars.get('db_connection'):
                config.session_vars['db_connection'].close_db()
            config.session_vars['db_connection'] = dao
        return dao
    return None


def create_sqlite_connection(
    db_path: str,
    set_as_default: bool = True,
    **kwargs
) -> Optional[HeSqliteDao]:
    """
    Create a SQLite connection.

    :param db_path: Path to SQLite database file
    :param set_as_default: Set this connection as the default global connection
    :return: HeSqliteDao instance or None if connection failed
    """
    from ..config import config

    dao = HeSqliteDao()
    if dao.connect(db_path, **kwargs):
        if set_as_default:
            # Close existing connection if any
            if config.session_vars.get('db_connection'):
                config.session_vars['db_connection'].close_db()
            config.session_vars['db_connection'] = dao
        return dao
    return None


def get_connection() -> Optional[HeDbDao]:
    """
    Get the current default database connection.

    :return: Current DAO instance or None
    """
    from ..config import config
    return config.session_vars.get('db_connection')


def close_connection() -> None:
    """
    Close the current default database connection.
    """
    from ..config import config
    dao = config.session_vars.get('db_connection')
    if dao:
        dao.close_db()
        config.session_vars['db_connection'] = None

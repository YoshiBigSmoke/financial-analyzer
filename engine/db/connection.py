"""
Conexión central a DuckDB.
Un solo archivo de base de datos, una sola conexión reutilizable.
"""

import duckdb
from pathlib import Path

# Ruta al archivo de base de datos (relativa al proyecto)
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "db" / "financial.duckdb"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

_connection: duckdb.DuckDBPyConnection | None = None


def get_connection() -> duckdb.DuckDBPyConnection:
    """
    Devuelve la conexión activa a DuckDB.
    La crea la primera vez (singleton).
    Si el WAL está corrompido, lo elimina y reintenta.
    """
    global _connection
    if _connection is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        wal_path = DB_PATH.with_suffix(DB_PATH.suffix + ".wal")
        try:
            _connection = duckdb.connect(str(DB_PATH))
        except Exception:
            # WAL corrompido — eliminarlo y reintentar
            if wal_path.exists():
                wal_path.unlink()
            _connection = duckdb.connect(str(DB_PATH))
        _init_schema(_connection)
    return _connection


def _init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """
    Ejecuta el schema.sql al iniciar si las tablas no existen.
    DuckDB no tiene executescript, se ejecuta statement por statement.
    """
    schema_sql = SCHEMA_PATH.read_text()
    for statement in schema_sql.split(";"):
        stmt = statement.strip()
        if stmt:
            conn.execute(stmt)


def close_connection() -> None:
    """
    Cierra la conexión limpiamente (llamar al cerrar la app).
    """
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None

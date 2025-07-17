import sqlite3
from sqlite3 import Connection, Cursor
from typing import Tuple


def db_initializer() -> Tuple[Connection, Cursor]:
    """
    Initialize the database.
    """
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()

    # Tabla de usuarios
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_id TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL
        )
        """
    )

    # Tabla de beneficiarios
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS beneficiaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            category TEXT
        )
    """
    )
    conn.commit()
    return conn, cursor

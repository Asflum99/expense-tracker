import sqlite3
from sqlite3 import Connection, Cursor
from typing import Tuple


def db_initializer() -> Tuple[Connection, Cursor]:
    """
    Initialize the database by creating the beneficiaries table
    if it doesn't exist.

    The table has the following columns:
        id: INTEGER PRIMARY KEY AUTOINCREMENT
        name: TEXT UNIQUE
        category: TEXT
    """
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()

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

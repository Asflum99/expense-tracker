import sqlite3


def db_initializer():
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
    conn.close()

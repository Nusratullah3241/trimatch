"""Adds columns that create_all() cannot add to an existing table.

SQLAlchemy create_all() creates missing tables but never alters existing
ones, so new columns on a table that already exists must be added by hand.
A real project would use Alembic for this.
"""
import sqlite3

conn = sqlite3.connect("data/trimatch.db")
cur = conn.cursor()

existing = {row[1] for row in cur.execute("PRAGMA table_info(match_runs)")}

wanted = {
    "applied_price_tolerance_pct": "FLOAT DEFAULT 2.0",
    "applied_absolute_tolerance": "FLOAT DEFAULT 500.0",
}

added = []
for column, spec in wanted.items():
    if column not in existing:
        cur.execute(f"ALTER TABLE match_runs ADD COLUMN {column} {spec}")
        added.append(column)

conn.commit()
conn.close()

if added:
    print("Added columns:", ", ".join(added))
else:
    print("Nothing to add - schema already up to date.")

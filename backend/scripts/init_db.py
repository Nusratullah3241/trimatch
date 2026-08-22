"""Creates all database tables. Run once."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, engine
from app import models  # noqa: F401 - importing registers the tables

Base.metadata.create_all(bind=engine)

print("Database created successfully.")
print("Tables:")
for table_name in Base.metadata.tables:
    print(f"   - {table_name}")
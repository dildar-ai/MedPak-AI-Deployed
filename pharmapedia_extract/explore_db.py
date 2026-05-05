import sqlite3
import sys

# Fix Windows terminal encoding
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r"d:\Pak Med AI\pharmapedia_extract\pharmapedia.db")
cursor = conn.cursor()

sep = "=" * 60
line = "-" * 60

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = [t[0] for t in cursor.fetchall()]
print(f"\n{sep}")
print(f"TOTAL TABLES FOUND: {len(tables)}")
print(f"{sep}")
print(", ".join(tables))

# For each table: schema + row count + 2 sample rows
for table in tables:
    print(f"\n{line}")
    print(f"TABLE: {table}")
    cursor.execute(f"PRAGMA table_info({table});")
    columns = cursor.fetchall()
    col_names = [c[1] for c in columns]
    print(f"COLUMNS ({len(col_names)}): {col_names}")

    cursor.execute(f"SELECT COUNT(*) FROM [{table}];")
    count = cursor.fetchone()[0]
    print(f"ROW COUNT: {count:,}")

    if count > 0:
        cursor.execute(f"SELECT * FROM [{table}] LIMIT 2;")
        rows = cursor.fetchall()
        print("SAMPLE ROWS:")
        for row in rows:
            print(f"  {row}")

conn.close()
print(f"\n{sep}")
print("Schema exploration complete!")

"""
MedPak AI — Live Prices Database
Persistent SQLite storage for scraped medicine prices.
Separate from the read-only pharmapedia.db — this database is read-write.

Table:
  live_prices (id, brand_name, price_pkr, source_url, source_name, scraped_at)
"""

import sqlite3
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from contextlib import contextmanager
from config import settings


# ── Connection helpers ────────────────────────────────────────────────────────

def _ensure_db():
    """Create the database file and table if they don't exist."""
    os.makedirs(os.path.dirname(settings.PRICES_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(settings.PRICES_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS live_prices (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_name  TEXT    NOT NULL,
            price_pkr   REAL    NOT NULL,
            source_url  TEXT,
            source_name TEXT,
            scraped_at  TEXT    NOT NULL,
            title       TEXT,
            pack_qty    INTEGER,
            pack_desc   TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_brand_name ON live_prices(brand_name)
    """)
    # Older schema had a unique (brand_name, source_name) index and no pack
    # columns — migrate in place (idempotent).
    conn.execute("DROP INDEX IF EXISTS idx_brand_source")
    existing = {r[1] for r in conn.execute("PRAGMA table_info(live_prices)").fetchall()}
    migrations = {
        "title": "ALTER TABLE live_prices ADD COLUMN title TEXT",
        "pack_qty": "ALTER TABLE live_prices ADD COLUMN pack_qty INTEGER",
        "pack_desc": "ALTER TABLE live_prices ADD COLUMN pack_desc TEXT",
    }
    for col, sql in migrations.items():
        if col not in existing:
            conn.execute(sql)
    conn.commit()
    conn.close()


# Initialize on module load
_ensure_db()


@contextmanager
def get_prices_conn():
    """Yield a read-write SQLite connection for live_prices.db."""
    conn = sqlite3.connect(settings.PRICES_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ── Write ─────────────────────────────────────────────────────────────────────

def save_prices(brand_name: str, results: list[dict]) -> int:
    """
    Save scraped prices into the live_prices table, replacing any previous
    rows for the brand (the fresh result set is the complete truth).

    Each result dict should have:
      - price_pkr (float)
      - source_url (str)
      - source (str) — used as source_name
      - scraped_at (str, ISO datetime)
      - title (str) — product listing title, e.g. "RISEK 20 MG 10 S"
      - pack_qty (int|None) — units in the pack, parsed from the title
      - pack_desc (str|None) — human label, e.g. "10 caps"

    Returns the number of rows inserted.
    """
    if not results:
        return 0

    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    with get_prices_conn() as conn:
        conn.execute("DELETE FROM live_prices WHERE brand_name = ?", (brand_name.strip(),))
        for r in results:
            price = r.get("price_pkr")
            if price is None or price <= 0:
                continue
            conn.execute("""
                INSERT INTO live_prices
                    (brand_name, price_pkr, source_url, source_name, scraped_at,
                     title, pack_qty, pack_desc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                brand_name.strip(),
                price,
                r.get("source_url", ""),
                r.get("source", "unknown"),
                r.get("scraped_at", now),
                r.get("title", ""),
                r.get("pack_qty"),
                r.get("pack_desc"),
            ))
            inserted += 1

        conn.commit()

    if inserted:
        print(f"[PRICES_DB] Saved {inserted} price(s) for '{brand_name}'")
    return inserted


# ── Read ──────────────────────────────────────────────────────────────────────

def get_stored_prices(
    brand_name: str,
    max_age_hours: int = 72,
) -> Optional[list[dict]]:
    """
    Return stored live prices for a brand if they exist and are fresh enough.
    Returns None if no prices found or all are older than max_age_hours.

    Returns list of dicts: {price_pkr, source_url, source_name, scraped_at}
    """
    if not brand_name:
        return None

    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    ).isoformat()

    with get_prices_conn() as conn:
        rows = conn.execute("""
            SELECT price_pkr, source_url, source_name, scraped_at,
                   title, pack_qty, pack_desc
            FROM live_prices
            WHERE brand_name = ? AND scraped_at >= ?
            ORDER BY price_pkr ASC
        """, (brand_name.strip(), cutoff)).fetchall()

    if not rows:
        return None

    return [dict(r) for r in rows]


def get_stored_prices_batch(
    brand_names: list[str],
    max_age_hours: int = 72,
) -> dict[str, list[dict]]:
    """
    Return fresh stored prices for MANY brands in one query (chunked to
    stay under SQLite's parameter limit).

    Returns {brand_name: [row dicts]} keyed by the spelling the CALLER used
    (stored spellings are matched case-insensitively). Brands with no fresh
    rows are simply absent from the result.
    """
    names = [n.strip() for n in brand_names or [] if n and n.strip()]
    if not names:
        return {}

    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    ).isoformat()

    # Map every stored spelling back to the requested spelling.
    requested = {n.lower(): n for n in names}

    out: dict[str, list[dict]] = {}
    with get_prices_conn() as conn:
        for i in range(0, len(names), 400):
            chunk = names[i:i + 400]
            placeholders = ",".join("?" for _ in chunk)
            rows = conn.execute(f"""
                SELECT brand_name, price_pkr, source_url, source_name, scraped_at,
                       title, pack_qty, pack_desc
                FROM live_prices
                WHERE brand_name COLLATE NOCASE IN ({placeholders})
                  AND scraped_at >= ?
                ORDER BY price_pkr ASC
            """, (*chunk, cutoff)).fetchall()
            for row in rows:
                r = dict(row)
                key = requested.get((r["brand_name"] or "").lower())
                if key is None:
                    continue
                out.setdefault(key, []).append({
                    "price_pkr": r["price_pkr"],
                    "source_url": r["source_url"],
                    "source_name": r["source_name"],
                    "scraped_at": r["scraped_at"],
                    "title": r.get("title", ""),
                    "pack_qty": r.get("pack_qty"),
                    "pack_desc": r.get("pack_desc"),
                })

    return out


def get_all_brand_prices(brand_name: str) -> list[dict]:
    """
    Return ALL stored prices for a brand regardless of age.
    Useful for admin/debug views.
    """
    with get_prices_conn() as conn:
        rows = conn.execute("""
            SELECT price_pkr, source_url, source_name, scraped_at
            FROM live_prices
            WHERE brand_name = ?
            ORDER BY scraped_at DESC
        """, (brand_name.strip(),)).fetchall()

    return [dict(r) for r in rows]


def get_best_stored_price(brand_name: str, max_age_hours: int = 72) -> Optional[float]:
    """
    Quick helper: return the lowest stored live price for a brand.
    Returns None if no fresh prices available.
    """
    results = get_stored_prices(brand_name, max_age_hours=max_age_hours)
    if not results:
        return None
    prices = [
        r["price_pkr"]
        for r in results
        if r.get("price_pkr") and 10 < r["price_pkr"] < 50000
    ]
    return min(prices) if prices else None


def preload_recent_prices(max_age_hours: int = 48) -> dict[str, list[dict]]:
    """
    Load all recent prices from DB into a dict keyed by lowercase brand name.
    Called on startup to warm the in-memory cache.
    """
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    ).isoformat()

    with get_prices_conn() as conn:
        rows = conn.execute("""
            SELECT brand_name, price_pkr, source_url, source_name, scraped_at,
                   title, pack_qty, pack_desc
            FROM live_prices
            WHERE scraped_at >= ?
            ORDER BY brand_name, price_pkr ASC
        """, (cutoff,)).fetchall()

    result: dict[str, list[dict]] = {}
    for row in rows:
        r = dict(row)
        key = r["brand_name"].lower().strip()
        if key not in result:
            result[key] = []
        result[key].append({
            "price_pkr": r["price_pkr"],
            "source_url": r["source_url"],
            "source_name": r["source_name"],
            "scraped_at": r["scraped_at"],
            "title": r.get("title", ""),
            "pack_qty": r.get("pack_qty"),
            "pack_desc": r.get("pack_desc"),
        })

    print(f"[PRICES_DB] Preloaded {len(rows)} price entries for {len(result)} brands")
    return result


# ── Stats / Admin ─────────────────────────────────────────────────────────────

def get_prices_db_stats() -> dict:
    """Return statistics about the live_prices database."""
    with get_prices_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS cnt FROM live_prices").fetchone()["cnt"]
        brands = conn.execute("SELECT COUNT(DISTINCT brand_name) AS cnt FROM live_prices").fetchone()["cnt"]
        newest = conn.execute("SELECT MAX(scraped_at) AS ts FROM live_prices").fetchone()["ts"]
        oldest = conn.execute("SELECT MIN(scraped_at) AS ts FROM live_prices").fetchone()["ts"]

    return {
        "total_entries": total,
        "unique_brands": brands,
        "newest_scrape": newest,
        "oldest_scrape": oldest,
    }


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    print("=== Live Prices DB Self-Test ===\n")

    # Save test prices
    test_results = [
        {"price_pkr": 25.50, "source": "servaid.com.pk", "source_url": "https://servaid.com.pk/panadol", "scraped_at": datetime.now(timezone.utc).isoformat()},
        {"price_pkr": 28.00, "source": "dawai.com.pk", "source_url": "https://dawai.com.pk/panadol", "scraped_at": datetime.now(timezone.utc).isoformat()},
    ]
    n = save_prices("Panadol", test_results)
    print(f"Saved {n} prices for Panadol")

    # Read back
    stored = get_stored_prices("Panadol")
    print(f"Stored prices: {json.dumps(stored, indent=2)}")

    # Best price
    best = get_best_stored_price("Panadol")
    print(f"Best price: Rs.{best}")

    # Stats
    stats = get_prices_db_stats()
    print(f"DB Stats: {json.dumps(stats, indent=2)}")

    print("\n=== All tests passed! ===")

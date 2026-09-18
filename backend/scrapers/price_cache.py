"""
MedPak AI — 3-Tier Price Cache

Tier 1: In-memory dict (instant, resets on restart)
Tier 2: live_prices.db SQLite (persistent, survives restarts)
Tier 3: Live scrape from web (slowest, updates both tiers)

On cache miss:  memory -> DB -> scrape -> save to both
On startup:     preload recent DB entries into memory
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from scrapers.price_scraper import scrape_live_price, _extract_strength
from database.prices_db import (
    save_prices,
    get_stored_prices,
    get_stored_prices_batch,
    preload_recent_prices,
)


# ── Configuration ─────────────────────────────────────────────────────────────

CACHE_TTL_SECONDS: int = 24 * 60 * 60   # 24 hours for in-memory cache
DB_MAX_AGE_HOURS: int = 72               # 72 hours for DB-stored prices
NEGATIVE_TTL_SECONDS: int = 600          # 10 min: don't re-scrape recent failures


# ── Cache Data Structure ──────────────────────────────────────────────────────

@dataclass
class CachedPrice:
    """A single in-memory cache entry with results and timestamp."""
    results: list[dict]
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_fresh(self) -> bool:
        age = (datetime.now(timezone.utc) - self.fetched_at).total_seconds()
        return age < CACHE_TTL_SECONDS


# The global in-memory cache (process-scoped, resets on restart)
_cache: dict[str, CachedPrice] = {}

# Lock to prevent duplicate concurrent fetches for the same key
_fetch_locks: dict[str, asyncio.Lock] = {}

# Negative cache: brands whose scrape recently failed / found nothing.
# Prevents hammering sources with hopeless retries every few seconds.
_negative_cache: dict[str, datetime] = {}


def _recently_failed(brand_name: str) -> bool:
    """True if a recent scrape attempt for this brand found nothing."""
    key = _cache_key(brand_name)
    ts = _negative_cache.get(key)
    if ts is None:
        return False
    if (datetime.now(timezone.utc) - ts).total_seconds() < NEGATIVE_TTL_SECONDS:
        return True
    _negative_cache.pop(key, None)  # expired
    return False


def _mark_failed(brand_name: str) -> None:
    _negative_cache[_cache_key(brand_name)] = datetime.now(timezone.utc)


def _clear_failed(brand_name: str) -> None:
    _negative_cache.pop(_cache_key(brand_name), None)


# ── Startup warm ─────────────────────────────────────────────────────────────

def warm_cache_from_db():
    """
    Called on application startup to preload recent prices from DB into memory.
    This ensures the cache is warm even after a server restart.
    """
    try:
        db_data = preload_recent_prices(max_age_hours=48)
        now = datetime.now(timezone.utc)
        loaded = 0
        for key, results in db_data.items():
            _cache[key] = CachedPrice(
                results=[_format_result(key, r) for r in results],
                fetched_at=now,
            )
            loaded += 1
        print(f"[CACHE] Warmed {loaded} brand entries from DB into memory")
    except Exception as e:
        print(f"[CACHE] Failed to warm cache from DB: {e}")


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _format_result(brand_name: str, r: dict) -> dict:
    """Normalize a DB row or scraper result into the canonical cache format."""
    title = r.get("title", "") or ""
    strength = r.get("strength_mg")
    if strength is None and title:
        strength = _extract_strength(title)  # re-derive for DB-loaded rows
    return {
        "brand_name": brand_name,
        "price_pkr": r["price_pkr"],
        "source_url": r.get("source_url", "") or "",
        "source": r.get("source_name") or r.get("source", "") or "",
        "scraped_at": r.get("scraped_at", "") or "",
        "title": title,
        "pack_qty": r.get("pack_qty"),
        "pack_desc": r.get("pack_desc"),
        "strength_mg": strength,
    }


def _cache_key(brand_name: str) -> str:
    return brand_name.lower().strip()


def get_cached_price(brand_name: str) -> list[dict] | None:
    """Return cached results if they exist in memory and are fresh."""
    key = _cache_key(brand_name)
    entry = _cache.get(key)
    if entry and entry.is_fresh():
        return entry.results
    return None


def set_cached_price(brand_name: str, results: list[dict]) -> None:
    """Store scraped results in the in-memory cache."""
    key = _cache_key(brand_name)
    _cache[key] = CachedPrice(results=results)
    _negative_cache.pop(key, None)


# ── Main public function ─────────────────────────────────────────────────────

async def get_or_fetch_price(
    brand_name: str, strength: str | None = None
) -> list[dict] | None:
    """
    Return live price data using 3-tier lookup:
      Tier 1: In-memory cache (instant)
      Tier 2: SQLite live_prices.db (fast, persistent)
      Tier 3: Live web scrape (slow, updates both tiers)

    `strength` (BRAND_DRUG.MG) is only used on a live scrape so the search
    queries name the right formulation ("Risek 20mg price in Pakistan").

    Returns list of price dicts, or None if no data available.
    """
    if not brand_name or not brand_name.strip():
        return None

    # ── Tier 1: In-memory cache ───────────────────────────────────────────
    cached = get_cached_price(brand_name)
    if cached is not None:
        return cached

    # ── Acquire per-key lock to prevent duplicate concurrent fetches ──────
    key = _cache_key(brand_name)
    if key not in _fetch_locks:
        _fetch_locks[key] = asyncio.Lock()

    async with _fetch_locks[key]:
        # Double-check after acquiring lock
        cached = get_cached_price(brand_name)
        if cached is not None:
            return cached

        # ── Tier 2: SQLite persistent DB ──────────────────────────────────
        db_results = get_stored_prices(brand_name, max_age_hours=DB_MAX_AGE_HOURS)
        if db_results:
            formatted = [_format_result(brand_name, r) for r in db_results]
            set_cached_price(brand_name, formatted)
            return formatted

        # ── Tier 3: Live web scrape ───────────────────────────────────────
        # Skip brands that recently failed so callers get a fast None
        # instead of re-waiting on a hopeless scrape.
        if _recently_failed(brand_name):
            return None

        try:
            results = await scrape_live_price(brand_name, strength)
        except Exception as e:
            print(f"[CACHE] Error scraping '{brand_name}': {e}")
            results = None
        if results:
            # Save to both tiers
            set_cached_price(brand_name, results)
            try:
                save_prices(brand_name, results)
            except Exception as e:
                print(f"[CACHE] Failed to save prices to DB for '{brand_name}': {e}")
            return results
        _mark_failed(brand_name)

    return None


# ── Batch parallel fetch ─────────────────────────────────────────────────────

async def get_or_fetch_prices_batch(
    brand_names: list[str],
    timeout: float = 5.0,
    strengths: dict[str, str] | None = None,
) -> dict[str, list[dict] | None]:
    """
    Batch-fetch live prices for multiple brands in parallel.
    Returns {brand_name: results_or_None} for each input brand.
    - Cached brands (memory/DB) return instantly.
    - Uncached brands are scraped concurrently with per-brand timeout.
    - `strengths` ({brand_name: "20 MG"}) sharpens the search queries.
    """
    results: dict[str, list[dict] | None] = {}
    to_scrape: list[str] = []

    # ── Step 1: Check cache/DB for each brand (instant) ───────────────────
    for name in brand_names:
        if not name or not name.strip():
            continue
        # Tier 1: In-memory cache
        cached = get_cached_price(name)
        if cached is not None:
            results[name] = cached
            continue

        # Tier 2: SQLite DB
        db_results = get_stored_prices(name, max_age_hours=DB_MAX_AGE_HOURS)
        if db_results:
            set_cached_price(name, [_format_result(name, r) for r in db_results])
            results[name] = _cache[_cache_key(name)].results
            continue

        # Need to scrape — unless it recently failed
        if _recently_failed(name):
            results[name] = None
            continue
        to_scrape.append(name)

    # ── Step 2: Scrape uncached brands in parallel ─────────────────────────
    if to_scrape:
        async def _fetch_one(name: str):
            try:
                result = await asyncio.wait_for(
                    scrape_live_price(name, (strengths or {}).get(name)),
                    timeout=timeout,
                )
                return name, result
            except asyncio.TimeoutError:
                print(f"[CACHE] Timeout scraping '{name}' ({timeout}s)")
                return name, None
            except Exception as e:
                print(f"[CACHE] Error scraping '{name}': {e}")
                return name, None

        tasks = [_fetch_one(name) for name in to_scrape]
        batch_results = await asyncio.gather(*tasks)

        for name, result in batch_results:
            results[name] = result
            if result:
                set_cached_price(name, result)
                try:
                    save_prices(name, result)
                except Exception as e:
                    print(f"[CACHE] Failed to save to DB for '{name}': {e}")
            else:
                _mark_failed(name)

    return results


# ── Best-result selection ─────────────────────────────────────────────────────

# Validity band for a listing price (mirrors the scraper's own filter).
_PRICE_MIN: float = 15.0
_PRICE_MAX: float = 30000.0
# A "pack" price below this per unit is not a pack price — it is either the
# price of a SINGLE unit ("10 caps for Rs 15.90") or junk ("100 caps Rs 1.83").
_PER_UNIT_MIN: float = 2.0


def select_best_result(
    results: list[dict] | None,
    strength_mg: float | None = None,
    form_name: str | None = None,
) -> dict | None:
    """
    Pick the most trustworthy listing from one brand's scraped results.

    Preference order:
      1. Listings with plausible per-unit economics — filters junk prices and
         listings that quote a SINGLE unit's price against a pack title.
      2. Listings whose strength matches the requested one (when known).
      3. Anything else valid (e.g. titles without pack info).
    Within the chosen pool the cheapest pack price wins.
    """
    valid = [
        r for r in (results or [])
        if r.get("price_pkr") and _PRICE_MIN <= r["price_pkr"] <= _PRICE_MAX
    ]
    if not valid:
        return None

    sane = [
        r for r in valid
        if not (r.get("pack_qty") and r["pack_qty"] > 1
                and r["price_pkr"] / r["pack_qty"] < _PER_UNIT_MIN)
    ]
    pool = sane or valid

    if form_name:
        f = form_name.strip().lower()
        syns = []
        if "inj" in f or "amp" in f or "vial" in f: syns = ["inj", "amp", "vial"]
        elif "tab" in f: syns = ["tab"]
        elif "cap" in f: syns = ["cap"]
        elif "syr" in f or "susp" in f: syns = ["syrup", "suspension", "liquid", "solution"]
        elif "gel" in f or "oint" in f or "cream" in f: syns = ["gel", "ointment", "cream", "topical"]
        elif "drop" in f: syns = ["drop"]
        elif "sach" in f: syns = ["sachet"]
        else: syns = [f]

        if syns:
            pool = [
                r for r in pool
                if any(s in r.get("title", "").lower() for s in syns)
            ]

    if not pool:
        return None

    if strength_mg:
        matching = [
            r for r in pool
            if r.get("strength_mg") is not None
            and abs(r["strength_mg"] - strength_mg) < 0.01
        ]
        if matching:
            pool = matching

    return min(pool, key=lambda r: r["price_pkr"])


def get_best_result(brand_name: str, strength_mg: float | None = None, form_name: str | None = None) -> dict | None:
    """
    Cheapest valid SAVED live result for a brand (memory → DB, never scrapes).
    Returns the full result dict incl. pack_qty / pack_desc / title, or None.
    """
    results = get_cached_price(brand_name)
    if results is None:
        db_results = get_stored_prices(brand_name, max_age_hours=DB_MAX_AGE_HOURS)
        if db_results:
            results = [_format_result(brand_name, r) for r in db_results]
            set_cached_price(brand_name, results)
    return select_best_result(results, strength_mg=strength_mg, form_name=form_name)


# ── Instant batch lookup (no scraping) ────────────────────────────────────────

def get_saved_prices_batch(brand_names: list[str]) -> dict[str, list[dict]]:
    """
    Saved results for many brands at once: memory first, then ONE batched DB
    query. NEVER scrapes — used for instant endpoint responses.
    Returns {brand_name: [results]} for brands that have saved prices, keyed
    by the exact spelling the caller used.
    """
    out: dict[str, list[dict]] = {}
    names: list[str] = []
    seen: set[str] = set()
    for name in brand_names or []:
        if not name or not name.strip():
            continue
        n = name.strip()
        key = _cache_key(n)
        if key in seen:
            continue
        seen.add(key)
        names.append(n)
        cached = get_cached_price(n)
        if cached is not None:
            out[n] = cached

    missing = [n for n in names if n not in out]
    if missing:
        db_rows = get_stored_prices_batch(missing, max_age_hours=DB_MAX_AGE_HOURS)
        for n, rows in db_rows.items():
            formatted = [_format_result(n, r) for r in rows]
            set_cached_price(n, formatted)
            out[n] = formatted

    return out


def pending_scrape_brands(brand_names: list[str]) -> list[str]:
    """
    Brands that need a live scrape RIGHT NOW: no fresh memory entry, no fresh
    DB rows, and no recent failed attempt. Input order is preserved.
    """
    names: list[str] = []
    seen: set[str] = set()
    for name in brand_names or []:
        if not name or not name.strip():
            continue
        n = name.strip()
        key = _cache_key(n)
        if key in seen:
            continue
        seen.add(key)
        if get_cached_price(n) is not None:
            continue
        if _recently_failed(n):
            continue  # recently scraped and found nothing — don't rehammer
        names.append(n)

    if not names:
        return []
    db_rows = get_stored_prices_batch(names, max_age_hours=DB_MAX_AGE_HOURS)
    return [n for n in names if not db_rows.get(n)]


# ── Background bulk scraping (all brands, simultaneously) ────────────────────

# In-flight bulk scrape jobs: key -> status dict
_scrape_jobs: dict[str, dict] = {}

BULK_CONCURRENCY: int = 10        # brands scraped at the same time
BULK_PER_BRAND_TIMEOUT: float = 25.0


def register_scrape_job(job_key: str, total: int) -> dict:
    """
    Create a job entry synchronously (before the response is sent) so the
    very first response can already report scrape progress to the client.

    `running` is True from registration ("a scrape is coming") while
    `task_started` flips True only when the background task actually begins
    executing — bulk_scrape_brands skips itself only on a genuine in-flight
    task, never on its own registration.
    """
    status = {
        "running": True,
        "task_started": False,
        "total": max(0, int(total)),
        "done": 0,
        "found": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    _scrape_jobs[job_key] = status
    return status


def get_scrape_status(job_key: str) -> dict | None:
    """Snapshot of a bulk scrape job's progress (None if never started)."""
    status = _scrape_jobs.get(job_key)
    return dict(status) if status else None


async def bulk_scrape_brands(
    job_key: str,
    brand_names: list[str],
    concurrency: int = BULK_CONCURRENCY,
    strengths: dict[str, str] | None = None,
) -> dict:
    """
    Scrape live prices for ALL given brands simultaneously (bounded by
    `concurrency`) and persist every result to live_prices.db for future use.

    `strengths` maps brand_name → DB strength ("20 MG") so each scrape
    searches for the right formulation ("Risek 20mg price in Pakistan").

    Designed as a FastAPI background task: the endpoint has already replied
    instantly with saved prices while this job fills in the rest. Progress is
    visible through get_scrape_status(job_key) so the frontend can poll.
    """
    existing = _scrape_jobs.get(job_key)
    if existing and existing.get("task_started"):
        return existing  # a task for this key is genuinely in flight

    pending = pending_scrape_brands(brand_names)
    status = register_scrape_job(job_key, len(pending))
    if not pending:
        status["running"] = False
        status["finished_at"] = status["started_at"]
        return status
    status["task_started"] = True

    print(
        f"[CACHE] Bulk scrape '{job_key}': fetching {len(pending)} brand(s) "
        f"with {concurrency} parallel workers"
    )
    sem = asyncio.Semaphore(concurrency)

    async def _scrape_one(name: str) -> None:
        async with sem:
            try:
                results = await asyncio.wait_for(
                    scrape_live_price(name, (strengths or {}).get(name)),
                    timeout=BULK_PER_BRAND_TIMEOUT,
                )
            except asyncio.TimeoutError:
                print(f"[CACHE] Bulk scrape: timeout for '{name}'")
                results = None
            except Exception as e:
                print(f"[CACHE] Bulk scrape: error for '{name}': {e}")
                results = None

        status["done"] += 1
        if results:
            status["found"] += 1
            set_cached_price(name, results)
            try:
                save_prices(name, results)  # persist for future requests
            except Exception as e:
                print(f"[CACHE] Failed to save prices for '{name}': {e}")
        else:
            _mark_failed(name)

    try:
        await asyncio.gather(
            *[_scrape_one(n) for n in pending], return_exceptions=True
        )
    finally:
        status["running"] = False
        status["task_started"] = False
        status["finished_at"] = datetime.now(timezone.utc).isoformat()
        print(
            f"[CACHE] Bulk scrape '{job_key}' finished: "
            f"{status['found']}/{status['total']} brands priced"
        )

    return status


def clear_cache() -> int:
    """Clear all in-memory cached entries. Returns count removed."""
    count = len(_cache)
    _cache.clear()
    _fetch_locks.clear()
    _negative_cache.clear()
    print(f"[CACHE] Cleared {count} cached price entries")
    return count


def get_cache_stats() -> dict:
    """Return stats about the in-memory cache."""
    total = len(_cache)
    fresh = sum(1 for v in _cache.values() if v.is_fresh())
    return {"total_entries": total, "fresh_entries": fresh, "stale_entries": total - fresh}

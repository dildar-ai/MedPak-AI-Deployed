"""
MedPak AI — Live Medicine Price Scraper

Strategy (sources tried in order):
  1. Dvago pharmacy — Pakistan's largest pharmacy chain. Product pages are
     server-rendered with clean JSON-LD prices, and the sitemaps enumerate
     ~24,000 product URLs with descriptive slugs
     (dvago.pk/p/risek-capsules-20-mg-2x7s), so products are looked up
     directly — no API key, no search engine, no rate limits.
  2. Shopify pharmacy search API — hopepharmacy.pk's /search/suggest.json
     returns clean JSON {title, price, url} (no search engine in the loop,
     immune to DDG/Google rate limits)
  3. DuckDuckGo HTML snippets — parse price from search result snippets
  4. Direct SSR pharmacy pages — DDG ``site:`` search, then fetch product pages
  5. Google search snippets — secondary search engine
  6. Bing search snippets — tertiary search engine

Queries are strength-aware: a brand with strength "20 MG" is searched as
"Risek 20mg price in Pakistan" so snippets refer to the same formulation.

Reliability features:
  - Rotates realistic User-Agents on every request.
  - DuckDuckGo 202 (bot challenge) skips to the next source immediately
    instead of hammering the same endpoint.
  - Retries only on transient network errors — empty results are never
    retried (the medicine simply is not on that source).

Note: dawaai.pk, dvago.pk and sehat.com.pk render their SEARCH results with
client-side JavaScript, so their HTML search pages carry no product data
(verified Sep 2026). Dawaai's internal Elasticsearch proxy is broken
server-side and its sitemap coverage is too sparse to be useful — Dvago's
is not (see Source 1), which is why Dvago is queried directly.

Known Pakistani pharmacy sites (SSR product pages):
  servaid.com.pk, hopepharmacy.pk, multanpluspharmacy.com,
  dawaai.com.pk, dvago.pk, sehat.com.pk, derma.pk

Design rules:
  - Never crash the caller — every failure returns None silently.
  - Uses httpx.AsyncClient for async HTTP with realistic headers.
  - Retry with backoff on transient failures.
"""

from __future__ import annotations

import json
import os
import random
import re
import time
import traceback
import urllib.parse
import asyncio
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup


# ── Shared HTTP config ────────────────────────────────────────────────────────

# Realistic desktop User-Agents, rotated per request so no single fingerprint
# gets rate-limited/blocked by search engines or pharmacy CDNs.
_USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]


def _random_headers(referer: str = "https://www.google.com/") -> dict:
    """Build a fresh header set with a randomly chosen User-Agent."""
    return {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": referer,
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
    }


class _SkipSource(Exception):
    """Raised when a source is rate-limited/blocked — retrying is pointless."""


_TIMEOUT = httpx.Timeout(connect=8.0, read=15.0, write=5.0, pool=5.0)

# Regex that handles all variants: "Rs.191", "Rs 191", "Rs .191", "PKR235"
_PRICE_RE = re.compile(
    r"(?:Rs\s*\.?\s*|PKR\s*|₨\s*)([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)

# Pharmacy sites with server-side rendered product pages
_SSR_DOMAINS = [
    "servaid.com.pk",
    "hopepharmacy.pk",
    "multanpluspharmacy.com",
    "dawaai.pk",
    "dvago.pk",
    "sehat.com.pk",
    "derma.pk",
]

# Shopify-based pharmacies with a public /search/suggest.json API.
# Queried FIRST — direct, structured JSON, immune to search-engine rate
# limits. Add more storefront base URLs here as they are discovered.
_SHOPIFY_STORES = [
    "https://hopepharmacy.pk",
]

# Retry configuration
_MAX_RETRIES = 2
_RETRY_DELAY = 1.5  # seconds, doubles each retry


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_price(text: str) -> float | None:
    """Extract numeric price from text like '1,234.50' -> 1234.50."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        val = float(cleaned)
        return val if val > 0 else None
    except (ValueError, TypeError):
        return None


def _valid_price(price: float | None) -> bool:
    """Pakistan medicine prices are typically Rs.15 - Rs.30,000."""
    return price is not None and 15 <= price <= 30000


def _strength_token(strength: str | None) -> str:
    """
    Clean a DB strength string for search queries.
      "20 MG|40 MG" → "20mg"   "250MG/5ML" → "250mg/5ml"   "1 G" → "1g"
    Returns "" when the string has nothing usable.
    """
    if not strength:
        return ""
    s = str(strength).split("|")[0].strip()
    s = re.sub(r"\s+", "", s).lower()
    return s if re.match(r"^\d", s) else ""


def _extract_real_url(ddg_href: str) -> str:
    """Extract real URL from DDG's redirect wrapper."""
    if "uddg=" in ddg_href:
        match = re.search(r"uddg=([^&]+)", ddg_href)
        if match:
            return urllib.parse.unquote(match.group(1))
    return ddg_href


def _brand_matches(brand_name: str, text: str) -> bool:
    """
    Check if a listing/snippet is for THIS brand — not a sibling variant.

    Token-set matching: every token of the brand name must appear in the
    text, and the text must not contain variant modifiers (EXTRA, CF, FORTE,
    …) that are not part of the brand name.  This stops e.g. the price of
    "Panadol Extra" being attached to plain "PANADOL", or "Panadol CF"
    picking up "Panadol Extra" prices.
    """
    brand_tokens = set(_norm_tokens(brand_name))
    if not brand_tokens:
        return False
    text_tokens = set(_norm_tokens(text))

    # 1. All brand tokens must be present (order-insensitive).
    if not brand_tokens.issubset(text_tokens):
        return False

    # 2. Extra tokens that indicate a DIFFERENT variant reject the match.
    extras = text_tokens - brand_tokens - _FILLER_TOKENS
    if extras & _VARIANT_MODIFIERS:
        return False

    return True


def _norm_tokens(text: str) -> list[str]:
    """Split text into uppercase alphanumeric tokens ("PANADOL-CF" → PANADOL, CF)."""
    return [t for t in re.split(r"[^A-Za-z0-9]+", (text or "").upper()) if t]


# Words that carry no variant meaning — safe to appear alongside the brand.
_FILLER_TOKENS = {
    "MG", "MCG", "ML", "G", "GM", "IU", "CC", "S", "X",
    "TABLET", "TABLETS", "TAB", "TABS", "CAP", "CAPS", "CAPSULE", "CAPSULES",
    "SYRUP", "SUSPENSION", "SUSP", "INJECTION", "INJECTIONS", "INJ", "INFUSION",
    "CREAM", "GEL", "DROPS", "DROP", "OINTMENT", "LOTION", "SPRAY", "SUPPOSITORY",
    "SACHET", "SACHETS", "PACK", "PACKS", "STRIP", "STRIPS", "BOX", "BOTTLE",
    "ORAL", "SOLUTION", "SUGAR", "FREE", "PESSARY", "PESSARIES", "VIAL", "VIALS",
    "AMPOULE", "AMPOULES", "PARACETAMOL", "PRICE", "PAKISTAN", "PKR", "RS",
    "BUY", "ONLINE", "SHOP", "PHARMACY", "OF", "THE", "AND", "WITH", "FOR",
}

# Product-line extensions — when these appear in a listing but are NOT part of
# the brand name being searched, the listing is a different variant.
_VARIANT_MODIFIERS = {
    "EXTRA", "CF", "ADVANCE", "ADVANCED", "EXTEND", "FORTE", "FORT", "PLUS",
    "PM", "NIGHT", "NIGHTIME", "GOLD", "BABY", "CHILD", "CHILDREN", "KIDS",
    "JR", "MAX", "ULTRA", "PRO", "DUO", "DS", "SS", "XL", "MULTI", "WOMEN",
    "MEN", "INSTA", "SLEEP", "MIGRAINE", "PERIOD", "COLIC", "ALLERGY",
    "CHESTY", "DAY", "WOMAN", "FEM", "MUSCLE", "JOINT", "RETARD", "EC",
    # Release/strength suffixes common in Pakistan: Risek DSR, Dilzem SR,
    # Brufen LA, Voltral CR, Tixylix DM, Losar OD, Convulex ER, Glucophage XR
    "DSR", "SR", "LA", "CR", "DR", "DM", "OD", "ER", "XR",
}


# ── Source 2: Shopify Pharmacy Search API ───────────────────────────────────

def _make_result(
    brand: str,
    price: float,
    source_url: str,
    source: str,
    title: str = "",
    pack: dict | None = None,
) -> dict:
    """
    Build one result row. `pack` (from _extract_pack_info) can be supplied
    directly when the caller has a MORE reliable text to parse than the
    display title (e.g. Dvago's machine-generated URL slug).
    """
    pack_info = pack if pack is not None else _extract_pack_info(title)
    strength = _extract_strength(title)
    return {
        "brand_name": brand,
        "price_pkr": price,
        "source_url": source_url,
        "source": source,
        "scraped_at": _now_iso(),
        "title": title,
        "pack_qty": pack_info["pack_qty"],
        "pack_desc": pack_info["pack_desc"],
        "strength_mg": strength,
    }


# ── Pack size / strength parsing from listing titles ────────────────────────

_UNIT_WORDS = {
    "CAPS": "caps", "CAP": "caps", "CAPSULE": "caps", "CAPSULES": "caps",
    "TABLETS": "tabs", "TABLET": "tabs", "TABS": "tabs", "TAB": "tabs",
    "SACHETS": "sachets", "SACHET": "sachets",
    "VIALS": "vials", "VIAL": "vials",
    "AMPOULES": "ampoules", "AMPOULE": "ampoules",
    "PENS": "pens", "PEN": "pens",
}


def _dvago_pack_from_name(name: str) -> dict | None:
    """
    Parse Dvago's parenthetical pack descriptions.

      "(1 Strip = 10 Tablets)"                          → 10 tabs
      "(1 Box = 3 Strips)(1 Strip = 7 Capsules)"        → 21 caps
      "(1 Pack = 2 Strips)(1 Strip = 10 Tablets)"       → 20 tabs

    Falls back to None when no parenthetical is found or the result is
    unreasonable.
    """
    if not name:
        return None
    pairs = re.findall(
        r"\(\s*1\s+([A-Za-z]+)\s*=\s*(\d+)\s+([A-Za-z]+)S?\s*\)",
        name,
    )
    if not pairs:
        return None
    total = 1
    for _, n, _ in pairs:
        total *= int(n)
    if total <= 1 or total >= 1000:
        return None
    unit_word = pairs[-1][2].upper()
    desc_map = {
        "TABLET": "tabs", "TABLETS": "tabs", "TAB": "tabs", "TABS": "tabs",
        "CAPSULE": "caps", "CAPSULES": "caps", "CAP": "caps", "CAPS": "caps",
    }
    return {"pack_qty": total, "pack_desc": f"{total} {desc_map.get(unit_word, 'units')}"}


def _extract_pack_info(title: str) -> dict:
    """
    Parse what a listing's price refers to from its title.

    "RISEK 20 MG 10 S"            → qty 10,  "10 units"
    "Risek 20Mg Capsules 14S"     → qty 14,  "14 caps"
    "Capsules 21S (Pack 3X7s)"    → qty 21,  "3×7"
    "Tablets 100S (10 X 10S)"     → qty 100, "10×10"
    "Syrup 120 Ml"                → qty None, "120 ml"

    Returns {pack_qty: int|None, pack_desc: str|None}.
    """
    original = (title or "").upper()
    qty, desc = None, None

    # Volume for liquids: "120 ML" — checked before strengths are stripped.
    # A volume is not a unit count, so no per-unit math is possible.
    vol = re.search(r"(\d+(?:\.\d+)?)\s*(ML|CC)\b", original)
    if vol:
        v = float(vol.group(1))
        if 5 <= v <= 2000:
            desc = f"{v:g} ml"
            qty = None

    # Strip strengths ("20 MG", "500 MCG", "10 ML", "1000 IU") so their
    # numbers can never be mistaken for pack counts — "20MG CAPSULES 14S"
    # must yield 14 caps, not 20.
    t = re.sub(r"\d+(?:\.\d+)?\s*(?:MG|MCG|ML|CC|IU|%)\b", " ", original)

    # a) Multiplier packs: "3X7s", "10 X 10S", "2x28"
    m = re.search(r"(\d+)\s*[X\u00d7]\s*(\d+)\s*'?S?\b", t)
    if m:
        n1, n2 = int(m.group(1)), int(m.group(2))
        if 1 < n1 < 100 and 1 < n2 < 100:
            qty, desc = n1 * n2, f"{n1}\u00d7{n2}"

    # b) Count with unit word — either order:
    #    "14 Capsules" / "21 CAPS"  or  "Capsules 21S" / "Tablets 100's"
    #    (count-after-unit requires a trailing S so "Tablet 500 Mg"-style
    #    strengths can't masquerade as pack counts)
    if qty is None:
        m = (
            re.search(
                r"(\d+)\s+(CAPS|CAPSULES|CAPSULE|TABLETS|TABLET|TABS|TAB|SACHETS|SACHET|VIALS|VIAL|AMPOULES|AMPOULE|PENS|PEN)\b",
                t,
            )
            or re.search(
                r"\b(CAPS|CAPSULES|CAPSULE|TABLETS|TABLET|TABS|TAB|SACHETS|SACHET|VIALS|VIAL|AMPOULES|AMPOULE|PENS|PEN)S?\s+(\d+)\s*'?\s*S\b",
                t,
            )
        )
        if m:
            if m.group(1).isdigit():
                n, unit = int(m.group(1)), m.group(2)
            else:
                unit, n = m.group(1), int(m.group(2))
            if 1 < n < 1000:
                qty, desc = n, f"{n} {_UNIT_WORDS[unit]}"

    # c) Trailing count: "10 S", "100S", "200'S"
    if qty is None:
        m = re.search(r"(\d+)\s*'?S\b", t)
        if m:
            n = int(m.group(1))
            if 1 < n < 1000:
                qty, desc = n, f"{n} units"

    # d) "Pack of 28" / "Pack Size 10"
    if qty is None:
        m = re.search(r"PACK\s*(?:SIZE)?\s*(?:OF)?\s*(\d+)\b", t)
        if m:
            n = int(m.group(1))
            if 1 < n < 1000:
                qty, desc = n, f"{n} units"

    # A pack of 1 tells the user nothing
    if qty is not None and qty <= 1:
        qty = None

    return {"pack_qty": qty, "pack_desc": desc}


def _extract_strength(title: str) -> float | None:
    """First strength in the title: 'Risek 20Mg Capsules' → 20.0 (per-mg basis)."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(MG|MCG)\b", (title or "").upper())
    if m:
        val = float(m.group(1))
        return val / 1000 if m.group(2) == "MCG" else val
    return None


async def _scrape_pharmacy_shopify(
    brand_name: str, strength: str | None = None
) -> list[dict] | None:
    """
    Query Shopify storefront search-suggest APIs directly (no search engine).

    ``GET {store}/search/suggest.json?q=<brand>&resources[type]=product``
    returns clean JSON: {resources: {results: {products: [{title, price, url}]}}}
    Immune to DDG/Google rate limits — this is why it runs early.
    (`strength` is unused here: the suggest API is fuzzy; strength matching
    happens later in select_best_result via each result's strength_mg.)
    """
    results: list[dict] = []
    query = brand_name.strip()

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        for base in _SHOPIFY_STORES:
            domain = urllib.parse.urlparse(base).netloc
            try:
                resp = await client.get(
                    f"{base}/search/suggest.json",
                    params={
                        "q": query,
                        "resources[type]": "product",
                        "resources[limit]": "10",
                    },
                    headers=_random_headers(f"{base}/"),
                )
            except Exception:
                continue  # store unreachable — try the next one
            if resp.status_code != 200:
                continue
            try:
                products = (
                    resp.json().get("resources", {}).get("results", {}).get("products", [])
                )
            except Exception:
                continue

            for p in products:
                title = (p.get("title") or "").strip()
                # Shopify fuzzy-matches loosely — a query for PANADOL returns
                # Panadol Extra, Panadol CF, … Only accept THIS variant.
                if not title or not _brand_matches(query, title):
                    continue
                price = _clean_price(str(p.get("price") or ""))
                if not _valid_price(price):
                    continue
                url = (p.get("url") or "").split("?")[0]  # drop tracking params
                if url.startswith("/"):
                    url = base + url
                results.append(_make_result(query, price, url, domain, title))

    return results if results else None


# ── Source 1: Dvago Pharmacy (direct product lookup) ─────────────────────────
# Dvago is one of Pakistan's largest pharmacy chains. Its product pages are
# server-rendered with clean JSON-LD prices, and its sitemaps enumerate every
# product URL with a descriptive slug:
#     https://www.dvago.pk/p/risek-capsules-20-mg-2x7s
# We download the product index once (disk-cached for a week), match the
# brand against URL slugs (variant-safe), and fetch matching product pages
# directly. No API key, no search engine, no rate limits.

_DVAGO_BASE = "https://www.dvago.pk"
_DVAGO_INDEX_TTL = 7 * 24 * 3600          # refresh the product index weekly
_DVAGO_RETRY_AFTER = 600                  # after a failed download, wait 10 min
_DVAGO_MAX_PRODUCTS = 5                   # product pages fetched per brand
_DVAGO_PAGE_SEM_LIMIT = 12                # global cap on concurrent page fetches
_DVAGO_INDEX_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "dvago_products.txt"
)

_dvago_index: list[str] | None = None     # product URLs, once loaded
_dvago_index_at: float = 0.0              # when the index was loaded
_dvago_failed_at: float = 0.0             # when the last download failed
_dvago_index_lock = asyncio.Lock()
_dvago_page_sem = asyncio.Semaphore(_DVAGO_PAGE_SEM_LIMIT)


def _dvago_sitemap_locs(text: str) -> list[str]:
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", text)


async def _dvago_download_index() -> list[str]:
    """Fetch Dvago's sitemap index → product sitemaps → flat URL list."""
    urls: list[str] = []
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(
            f"{_DVAGO_BASE}/sitemap.xml", headers=_random_headers(f"{_DVAGO_BASE}/")
        )
        resp.raise_for_status()
        product_maps = [
            u for u in _dvago_sitemap_locs(resp.text) if "product-sitemap" in u
        ]
        for sm in product_maps:
            r2 = await client.get(sm, headers=_random_headers(_DVAGO_BASE))
            if r2.status_code == 200:
                urls.extend(u for u in _dvago_sitemap_locs(r2.text) if "/p/" in u)
    return urls


async def _dvago_get_index() -> list[str]:
    """Product URL index — memory → disk cache → live download (weekly)."""
    global _dvago_index, _dvago_index_at, _dvago_failed_at

    if _dvago_index is not None:
        if time.time() - _dvago_index_at < _DVAGO_INDEX_TTL:
            return _dvago_index
    elif time.time() - _dvago_failed_at < _DVAGO_RETRY_AFTER:
        return []  # download failed recently — don't hammer the site

    async with _dvago_index_lock:
        # Another coroutine may have refreshed the index while we waited.
        if _dvago_index is not None and time.time() - _dvago_index_at < _DVAGO_INDEX_TTL:
            return _dvago_index

        # Disk cache (survives restarts — ~24k URLs are worth keeping).
        try:
            if (
                os.path.exists(_DVAGO_INDEX_PATH)
                and time.time() - os.path.getmtime(_DVAGO_INDEX_PATH) < _DVAGO_INDEX_TTL
            ):
                with open(_DVAGO_INDEX_PATH, encoding="utf-8") as f:
                    urls = [line.strip() for line in f if line.strip()]
                if urls:
                    _dvago_index, _dvago_index_at = urls, time.time()
                    print(f"[SCRAPER] Dvago index loaded from disk: {len(urls)} products")
                    return _dvago_index
        except Exception:
            pass

        try:
            urls = await _dvago_download_index()
        except Exception as e:
            print(f"[SCRAPER] Dvago sitemap download failed: {e}")
            _dvago_failed_at = time.time()
            return _dvago_index or []

        if urls:
            _dvago_index, _dvago_index_at = urls, time.time()
            try:
                with open(_DVAGO_INDEX_PATH, "w", encoding="utf-8") as f:
                    f.write("\n".join(urls))
            except Exception:
                pass
            print(f"[SCRAPER] Dvago index downloaded: {len(urls)} products")
        return _dvago_index or []


async def preload_dvago_index() -> None:
    """Warm the Dvago product index (fire-and-forget at app startup)."""
    try:
        await _dvago_get_index()
    except Exception:
        pass


async def _scrape_dvago(brand_name: str, strength: str | None = None) -> list[dict] | None:
    """
    Look the brand up in Dvago's product index and fetch matching product
    pages — authoritative pharmacy prices with pack info in the names.
    """
    query = brand_name.strip()
    index = await _dvago_get_index()
    if not index:
        return None

    # Candidate products: the URL slug must be for THIS brand (variant-safe —
    # "panadol" never matches "imp-panadol-advance-optzr-72s").
    brand_tokens = set(_norm_tokens(query))
    if not brand_tokens:
        return None
    candidates: list[tuple[str, str]] = []
    for url in index:
        slug = url.rsplit("/p/", 1)[-1]
        text_tokens = set(_norm_tokens(slug.replace("-", " ")))
        if not brand_tokens.issubset(text_tokens):
            continue
        extras = text_tokens - brand_tokens - _FILLER_TOKENS
        if extras & _VARIANT_MODIFIERS:
            continue
        candidates.append((url, slug))
    if not candidates:
        return None

    # When the strength is known, look at products of that strength first —
    # exact selection still happens later via each result's strength_mg.
    tok = _strength_token(strength)
    if tok:
        digits = re.sub(r"\D", "", tok)
        if digits:
            candidates.sort(key=lambda c: digits not in c[1].replace("-", ""))

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        async def _fetch_product(url: str, slug: str) -> dict | None:
            try:
                async with _dvago_page_sem:
                    r = await client.get(
                        url, headers=_random_headers(f"{_DVAGO_BASE}/")
                    )
                if r.status_code != 200:
                    return None
                soup = BeautifulSoup(r.text, "html.parser")
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        data = json.loads(script.string or "")
                    except Exception:
                        continue
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        types = item.get("@type") or []
                        types = types if isinstance(types, list) else [types]
                        if "Product" not in types and "Drug" not in types:
                            continue
                        name = str(item.get("name") or "").strip()
                        offers = item.get("offers") or {}
                        if isinstance(offers, list):
                            offers = offers[0] if offers else {}
                        price = _clean_price(str(offers.get("price", "")))
                        if not name or not _valid_price(price):
                            continue
                        currency = str(offers.get("priceCurrency") or "").upper()
                        if currency and currency not in ("PKR", "RS"):
                            continue
                        if "outofstock" in str(offers.get("availability") or "").lower():
                            continue  # stale price signal — product unavailable
                        slug_words = slug.replace("-", " ")
                        if not _brand_matches(query, f"{name} {slug_words}"):
                            continue
                        # The canonical URL and description carry the CURRENT
                        # pack ("risek-cap-20-mg-21s" / "RISEK CAP 20 MG 21'S");
                        # sitemap slugs can be stale — the old "2x7s" URL
                        # serves the same 21s product today.
                        canon = str(item.get("url") or "").strip()
                        canon_words = (
                            canon.rstrip("/").rsplit("/p/", 1)[-1].replace("-", " ")
                            if "/p/" in canon else ""
                        )
                        m = re.search(
                            r"Buy\s+(.+?)\s+from\s+",
                            str(item.get("description") or ""),
                            re.IGNORECASE,
                        )
                        desc_name = m.group(1).strip() if m else ""
                        # Pack info priority:
                        #   1. Description product name ("RISEK CAP 20 MG 21'S")
                        #   2. Display-name parentheticals
                        #      ("(1 Box = 3 Strips)(1 Strip = 7 Capsules)" → 21,
                        #       "(1 Strip = 10 Tablets)" → 10)
                        #   3. Canonical URL slug (current pack)
                        #   4. (possibly stale/misleading) sitemap slug.
                        pack = None
                        if desc_name:
                            pack = _extract_pack_info(desc_name)
                            if pack["pack_qty"] is None and pack["pack_desc"] is None:
                                pack = None
                        if pack is None:
                            pack = _dvago_pack_from_name(name)
                        if pack is None and canon_words:
                            pack = _extract_pack_info(canon_words)
                            if pack["pack_qty"] is None and pack["pack_desc"] is None:
                                pack = None
                        if pack is None:
                            pack = _extract_pack_info(slug_words)
                            if pack["pack_qty"] is None and pack["pack_desc"] is None:
                                pack = None
                        # Display names carry parenthetical strip descriptions
                        # ("(1 Strip = 7 Capsules)") that are NOT the pack being
                        # sold — strip them so the title can never be parsed as
                        # a 7-unit pack.
                        clean_name = re.sub(r"\s*\([^)]*\)", " ", name).strip() or name
                        title = desc_name or clean_name
                        if _extract_strength(title) is None:
                            title = f"{canon_words or slug_words} {title}".strip()
                        return _make_result(
                            query, price,
                            canon if "/p/" in canon else url,
                            "dvago.pk", title, pack=pack,
                        )
                return None
            except Exception:
                return None

        fetched = await asyncio.gather(
            *[_fetch_product(u, s) for u, s in candidates[:_DVAGO_MAX_PRODUCTS]]
        )

    results = [r for r in fetched if r]
    return results if results else None


# ── Source 3: DuckDuckGo Snippet Prices ───────────────────────────────────────

async def _scrape_duckduckgo_snippets(
    brand_name: str, strength: str | None = None
) -> list[dict] | None:
    """
    Parse price from DuckDuckGo HTML search result snippets.
    """
    results: list[dict] = []
    query = brand_name.strip()
    tok = _strength_token(strength)
    q = f"{query} {tok}".strip()
    search_q = f"{q} price Pakistan Rs"

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        try:
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": search_q},
                headers=_random_headers("https://html.duckduckgo.com/"),
            )
            if resp.status_code == 202:
                # DDG bot-challenge — retrying the same IP instantly never works
                raise _SkipSource("DuckDuckGo rate-limited (HTTP 202)")
            if resp.status_code != 200:
                print(f"[SCRAPER] DDG status {resp.status_code}")
                return None

            soup = BeautifulSoup(resp.text, "html.parser")

            for result_div in soup.select(".result"):
                try:
                    snippet_el = result_div.select_one(".result__snippet")
                    title_el = result_div.select_one(".result__a")
                    url_el = result_div.select_one(".result__url")
                    if not snippet_el:
                        continue

                    snippet = snippet_el.get_text(" ", strip=True)
                    title = title_el.get_text(strip=True) if title_el else ""
                    source_url = url_el.get_text(strip=True) if url_el else ""

                    if not _brand_matches(query, f"{title} {snippet}"):
                        continue

                    price_matches = _PRICE_RE.findall(snippet)
                    for price_str in price_matches:
                        price = _clean_price(price_str)
                        if _valid_price(price):
                            results.append(
                                _make_result(
                                    query,
                                    price,
                                    f"https://{source_url}" if source_url else "",
                                    source_url.split("/")[0] if source_url else "duckduckgo",
                                    title,
                                )
                            )
                except Exception:
                    continue

        except _SkipSource:
            raise
        except Exception:
            traceback.print_exc()

    return results if results else None


# ── Source 4: Direct SSR Pharmacy Pages ───────────────────────────────────────

async def _scrape_direct_pages(
    brand_name: str, strength: str | None = None
) -> list[dict] | None:
    """
    Search DuckDuckGo for product pages on SSR pharmacy sites,
    then fetch those pages directly and parse prices from HTML.
    """
    results: list[dict] = []
    query = brand_name.strip()
    tok = _strength_token(strength)
    q = f"{query} {tok}".strip()

    search_q = f"{q} " + " OR ".join(f"site:{d}" for d in _SSR_DOMAINS)

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        try:
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": search_q},
                headers=_random_headers("https://html.duckduckgo.com/"),
            )
            if resp.status_code == 202:
                raise _SkipSource("DuckDuckGo rate-limited (HTTP 202)")
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")

            page_urls: list[str] = []
            for result_div in soup.select(".result"):
                link_el = result_div.select_one(".result__a")
                if not link_el:
                    continue
                href = link_el.get("href", "")
                real_url = _extract_real_url(href)
                if any(d in real_url for d in _SSR_DOMAINS):
                    page_urls.append(real_url)

            for page_url in page_urls[:3]:
                try:
                    page_resp = await client.get(
                        page_url, headers=_random_headers("https://www.google.com/")
                    )
                    if page_resp.status_code != 200:
                        continue

                    page_soup = BeautifulSoup(page_resp.text, "html.parser")
                    page_text = page_soup.get_text(" ", strip=True)
                    # Product page title — e.g. "NORAN 20MG CAPSULES 14S - ..."
                    # (parsed into pack info by _make_result)
                    page_title = (
                        page_soup.title.get_text(strip=True) if page_soup.title else ""
                    )

                    if not _brand_matches(query, page_text):
                        continue

                    domain = urllib.parse.urlparse(page_url).netloc

                    # Strategy A: JSON-LD structured data
                    for script in page_soup.find_all("script", type="application/ld+json"):
                        try:
                            data = json.loads(script.string or "")
                            items = data if isinstance(data, list) else [data]
                            for item in items:
                                if item.get("@type") in ("Product", "Drug"):
                                    offers = item.get("offers", {})
                                    if isinstance(offers, list):
                                        offers = offers[0] if offers else {}
                                    price = _clean_price(str(offers.get("price", "")))
                                    if _valid_price(price):
                                        results.append(
                                            _make_result(
                                                query, price, page_url, domain,
                                                str(item.get("name") or "").strip() or page_title,
                                            )
                                        )
                        except Exception:
                            pass

                    # Strategy B: CSS price selectors (WooCommerce/Shopify)
                    if not results:
                        for selector in [
                            ".price .woocommerce-Price-amount",
                            ".price .amount",
                            ".price",
                            ".product-price",
                            ".current-price",
                            ".ProductMeta__Price",
                            "span.price",
                            ".product__price",
                        ]:
                            for el in page_soup.select(selector):
                                el_text = el.get_text(strip=True)
                                price_matches = _PRICE_RE.findall(el_text)
                                for ps in price_matches:
                                    price = _clean_price(ps)
                                    if _valid_price(price):
                                        results.append(
                                            _make_result(query, price, page_url, domain, page_title)
                                        )
                                        break
                            if results:
                                break

                    # Strategy C: Regex fallback on full page text
                    if not results:
                        for ps in _PRICE_RE.findall(page_text)[:8]:
                            price = _clean_price(ps)
                            if _valid_price(price):
                                results.append(
                                    _make_result(query, price, page_url, domain, page_title)
                                )
                                break

                    if results:
                        break

                except Exception:
                    continue

        except _SkipSource:
            raise
        except Exception:
            traceback.print_exc()

    return results if results else None


# ── Source 5: Google Search Snippets ──────────────────────────────────────────

async def _scrape_google_snippets(
    brand_name: str, strength: str | None = None
) -> list[dict] | None:
    """
    Parse prices from Google search result snippets.
    Uses google.com/search with plain HTML user-agent.
    """
    results: list[dict] = []
    query = brand_name.strip()
    tok = _strength_token(strength)
    q = f"{query} {tok}".strip()
    search_q = f"{q} price in Pakistan"

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        try:
            resp = await client.get(
                "https://www.google.com/search",
                params={"q": search_q, "hl": "en"},
                headers=_random_headers("https://www.google.com/"),
            )
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")

            # Google wraps results in divs with class "g"
            for g_div in soup.select("div.g"):
                try:
                    text = g_div.get_text(" ", strip=True)

                    if not _brand_matches(query, text):
                        continue

                    # Result heading is the product listing title
                    heading_el = g_div.select_one("h3")
                    title = heading_el.get_text(strip=True) if heading_el else ""

                    price_matches = _PRICE_RE.findall(text)
                    for price_str in price_matches[:3]:
                        price = _clean_price(price_str)
                        if _valid_price(price):
                            # Extract source URL from the link
                            link_el = g_div.select_one("a[href]")
                            source_url = link_el["href"] if link_el else ""
                            domain = ""
                            if source_url:
                                parsed = urllib.parse.urlparse(source_url)
                                domain = parsed.netloc or source_url.split("/")[0]

                            results.append(
                                _make_result(
                                    query,
                                    price,
                                    source_url,
                                    domain or "google",
                                    title,
                                )
                            )
                            break
                except Exception:
                    continue

        except Exception:
            traceback.print_exc()

    return results if results else None


# ── Source 6: Bing Search Snippets ────────────────────────────────────────────

async def _scrape_bing_snippets(
    brand_name: str, strength: str | None = None
) -> list[dict] | None:
    """
    Parse prices from Bing search result snippets.
    Bing is far less aggressive about blocking plain HTTP clients
    than Google, making it a reliable last resort.
    """
    results: list[dict] = []
    query = brand_name.strip()
    tok = _strength_token(strength)
    q = f"{query} {tok}".strip()
    search_q = f"{q} price Pakistan Rs"

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        try:
            resp = await client.get(
                "https://www.bing.com/search",
                params={"q": search_q, "setlang": "en"},
                headers=_random_headers("https://www.bing.com/"),
            )
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")

            # Bing wraps organic results in <li class="b_algo">
            for li in soup.select("li.b_algo"):
                try:
                    text = li.get_text(" ", strip=True)
                    if not text or not _brand_matches(query, text):
                        continue

                    link_el = li.select_one("h2 a[href]")
                    source_url = link_el["href"] if link_el else ""
                    # The h2 link text is the result (product) title
                    title = link_el.get_text(strip=True) if link_el else ""
                    domain = ""
                    if source_url:
                        parsed = urllib.parse.urlparse(source_url)
                        domain = parsed.netloc or source_url.split("/")[0]

                    for ps in _PRICE_RE.findall(text)[:3]:
                        price = _clean_price(ps)
                        if _valid_price(price):
                            results.append(
                                _make_result(query, price, source_url, domain or "bing", title)
                            )
                            break
                except Exception:
                    continue

        except Exception:
            traceback.print_exc()

    return results if results else None


# ── Retry wrapper ─────────────────────────────────────────────────────────────

async def _with_retry(
    fn, brand_name: str, source_name: str, strength: str | None = None
) -> list[dict] | None:
    """
    Execute a scraper function with retry on transient network errors.

    - _SkipSource (e.g. DDG 202 bot-challenge) aborts immediately —
      retrying the same rate-limited endpoint never helps.
    - Empty results are NOT retried: if a source has no price for this
      medicine, hammering it again just delays the next source.
    """
    for attempt in range(_MAX_RETRIES + 1):
        try:
            results = await fn(brand_name, strength)
            if results:
                return results
            return None  # empty = genuinely not on this source
        except _SkipSource as e:
            print(f"[SCRAPER] {source_name} skipped for '{brand_name}': {e}")
            return None
        except Exception as e:
            if attempt < _MAX_RETRIES:
                delay = _RETRY_DELAY * (2 ** attempt)
                print(f"[SCRAPER] {source_name} attempt {attempt+1} failed for '{brand_name}': {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                print(f"[SCRAPER] {source_name} all attempts failed for '{brand_name}': {e}")
    return None


# ── Public API ────────────────────────────────────────────────────────────────

async def scrape_live_price(
    brand_name: str, strength: str | None = None
) -> list[dict] | None:
    """
    Scrape live PKR medicine prices from multiple sources.

    `strength` (e.g. "20 MG" from BRAND_DRUG.MG) is folded into search
    queries ("Risek 20mg price in Pakistan") so results refer to the same
    formulation, and lets direct sources prefer matching products.

    Returns list of {brand_name, price_pkr, source_url, source, scraped_at,
    title, pack_qty, pack_desc, strength_mg} or None if all sources fail.
    Never raises.
    """
    if not brand_name or not brand_name.strip():
        return None

    sources = [
        ("Dvago Pharmacy", _scrape_dvago),
        ("Shopify Pharmacy", _scrape_pharmacy_shopify),
        ("DuckDuckGo", _scrape_duckduckgo_snippets),
        ("Direct Pharmacy", _scrape_direct_pages),
        ("Google", _scrape_google_snippets),
        ("Bing", _scrape_bing_snippets),
    ]

    for source_name, scraper_fn in sources:
        try:
            results = await _with_retry(scraper_fn, brand_name, source_name, strength)
            if results:
                # Deduplicate by (price, title) — same brand can legitimately
                # appear in several pack sizes with different prices.
                seen: set[tuple] = set()
                unique = [
                    r for r in results
                    if not ((r["price_pkr"], r.get("title", "")) in seen
                            or seen.add((r["price_pkr"], r.get("title", ""))))
                ]
                print(
                    f"[SCRAPER] OK {source_name}: {len(unique)} price(s) for '{brand_name}' -> "
                    + ", ".join(f"Rs.{r['price_pkr']} ({r.get('pack_desc') or r['source']})" for r in unique[:3])
                )
                return unique
        except Exception:
            print(f"[SCRAPER] FAIL {source_name} for '{brand_name}':")
            traceback.print_exc()

    print(f"[SCRAPER] No live prices found for '{brand_name}'")
    return None


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    async def main():
        for name, strength in [("Risek", "20 MG"), ("Panadol", None), ("Augmentin", "625 MG")]:
            print(f"\n{'='*60}")
            print(f"  Searching: {name} ({strength or 'any strength'})")
            print(f"{'='*60}")
            results = await scrape_live_price(name, strength)
            if results:
                for r in results[:3]:
                    print(
                        f"  Rs.{r['price_pkr']} — {r['source']} — {r.get('title', '')[:60]}"
                        f" — pack={r.get('pack_desc')} str={r.get('strength_mg')}"
                    )
            else:
                print("  No results.")

    asyncio.run(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import math
import random
import logging
import concurrent.futures as futures
from typing import List, Dict, Any, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import urllib3

# ---------------------- Config ----------------------
RENAS_PAGE_URL = "https://renascene.com/ps3/?target=list&ord=desc&page={page}"
TOTAL_PAGES = 41
REQUEST_TIMEOUT = 30
MAX_WORKERS = 8
RETRY_COUNT = 3
BACKOFF_BASE = 1.6
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
)
OUTPUT_FILENAME = "ps3_updates.json"
VERIFY_SSL = False  # set to True if your CA chain is correct
# ----------------------------------------------------
# Suppress warnings when verification is disabled
if not VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


def http_get(session: requests.Session, url: str, retries: int = RETRY_COUNT) -> Optional[requests.Response]:
    for attempt in range(retries):
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT, verify=VERIFY_SSL)
            if resp.status_code == 200:
                return resp
            elif resp.status_code in (429, 500, 502, 503, 504):
                delay = (BACKOFF_BASE ** attempt) + random.uniform(0, 0.5)
                logging.warning(f"GET {url} -> {resp.status_code}, retrying in {delay:.2f}s...")
                time.sleep(delay)
            elif resp.status_code in (403, 404):
                # No update XML for this ID or blocked; treat as no updates without retry noise
                logging.info(f"GET {url} -> {resp.status_code}")
                return None
            else:
                logging.warning(f"GET {url} -> {resp.status_code}, not retrying.")
                return None
        except requests.exceptions.SSLError as e:
            # If verification is enabled and fails, fall back to disable verification once
            if VERIFY_SSL and attempt == 0:
                logging.warning(f"SSL error on {url}, retrying without verification...")
                try:
                    resp = session.get(url, timeout=REQUEST_TIMEOUT, verify=False)
                    if resp.status_code == 200:
                        return resp
                except Exception:
                    pass
            delay = (BACKOFF_BASE ** attempt) + random.uniform(0, 0.5)
            logging.warning(f"GET {url} raised SSLError({e}), retrying in {delay:.2f}s...")
            time.sleep(delay)
        except requests.RequestException as e:
            delay = (BACKOFF_BASE ** attempt) + random.uniform(0, 0.5)
            logging.warning(f"GET {url} raised {e!r}, retrying in {delay:.2f}s...")
            time.sleep(delay)
    logging.error(f"GET {url} failed after {retries} retries.")
    return None


def find_main_table(soup: BeautifulSoup) -> Optional[Any]:
    expected_headers = ["EX", "ID", "REGION", "TITLE", "FOLDER", "DISC ID", "NFO", "RELEASED", "STREET", "NUKE", "SIZE", "TYPE"]
    tables = soup.find_all("table")
    for tbl in tables:
        # Try to read header cells
        header_cells = tbl.find_all("th")
        headers = [h.get_text(strip=True).upper() for h in header_cells]
        # Some tables may put headers in first row as td strong
        if not headers:
            first_tr = tbl.find("tr")
            if first_tr:
                headers = [td.get_text(strip=True).upper() for td in first_tr.find_all("td")]
        # Loose check: ensure all expected headers appear in sequence
        if headers and all(h in headers for h in expected_headers):
            return tbl
    # Fallback: choose the largest table by row count
    if tables:
        return max(tables, key=lambda t: len(t.find_all("tr")))
    return None


def parse_renascene_page(session: requests.Session, page: int) -> List[Dict[str, Any]]:
    url = RENAS_PAGE_URL.format(page=page)
    resp = http_get(session, url)
    if not resp:
        logging.error(f"Failed to fetch renascene page {page}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    table = find_main_table(soup)
    if not table:
        logging.error(f"Could not locate the data table on page {page}")
        return []

    rows = table.find_all("tr")

    # Build header map from the first row containing th/td header-like cells
    header_row = None
    for tr in rows:
        if tr.find_all("th"):
            header_row = tr
            break
    if header_row is None and rows:
        header_row = rows[0]

    def norm(s: str) -> str:
        return " ".join((s or "").upper().split())

    headers = [norm(c.get_text(strip=True)) for c in header_row.find_all(["th", "td"])]
    col_index: Dict[str, int] = {}
    wanted = [
        "EX", "ID", "REGION", "TITLE", "FOLDER", "DISC ID", "NFO", "RELEASED", "STREET", "NUKE", "SIZE", "TYPE"
    ]
    for i, h in enumerate(headers):
        if h in wanted and h not in col_index:
            col_index[h] = i

    items: List[Dict[str, Any]] = []
    # Iterate data rows (skip header_row)
    for tr in rows:
        if tr is header_row:
            continue
        tds = tr.find_all("td")
        if not tds:
            continue

        def td_text_by_header(hname: str) -> str:
            idx = col_index.get(hname)
            if idx is None or idx >= len(tds):
                return ""
            return tds[idx].get_text(strip=True)

        def td_link_by_header(hname: str) -> Optional[str]:
            idx = col_index.get(hname)
            if idx is None or idx >= len(tds):
                return None
            a = tds[idx].find("a")
            if a and a.get("href"):
                return requests.compat.urljoin(resp.url, a["href"])
            return None

        ex = td_text_by_header("EX")
        id_ = td_text_by_header("ID")
        region = td_text_by_header("REGION")
        title = td_text_by_header("TITLE")
        folder = td_text_by_header("FOLDER")
        disc_id = td_text_by_header("DISC ID").upper()
        nfo_link = td_link_by_header("NFO")
        released = td_text_by_header("RELEASED")
        street = td_text_by_header("STREET")
        nuke = td_text_by_header("NUKE")
        size = td_text_by_header("SIZE")
        type_ = td_text_by_header("TYPE")

        # Gather any row links (for fallback title id resolution)
        row_links: List[str] = []
        for td in tds:
            for a in td.find_all("a"):
                href = a.get("href")
                if href:
                    row_links.append(requests.compat.urljoin(resp.url, href))

        # Build the item even if disc_id is empty; we may resolve via NFO later
        items.append({
            "EX": ex,
            "ID": id_,
            "REGION": region,
            "TITLE": title,
            "FOLDER": folder,
            "DISC_ID": disc_id,
            "NFO": nfo_link,
            "ROW_LINKS": row_links,
            "RELEASED": released,
            "STREET": street,
            "NUKE": nuke,
            "SIZE": size,
            "TYPE": type_,
        })
    return items


def parse_ps3_update_xml(xml_bytes: bytes) -> Dict[str, Any]:
    """
    Parse PS3 update XML, extracting:
    - NPDRM package updates: version, url, sha1sum, size
    - DRM-free updates if present: url, sha1sum, size (paired with versions by index when possible)
    """
    updates: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return {"updates": updates}

    # NPDRM packages
    pkg_versions: List[str] = []
    for pkg in root.iter("package"):
        ver = pkg.get("version")
        url = pkg.get("url")
        sha1 = pkg.get("sha1sum")
        size = pkg.get("size")
        if ver:
            pkg_versions.append(ver)
        if url:
            entry = {
                "type": "NPDRM",
                "version": ver,
                "url": url,
                "sha1": sha1,
                "size_bytes": int(size) if size and size.isdigit() else None,
                "filename": os.path.basename(url),
            }
            updates.append(entry)

    # DRM-free updates (if present). Some XMLs include <url url="" sha1sum="" size=""> nodes.
    drmfree_nodes = list(root.iter("url"))
    if drmfree_nodes:
        # Try pairing by index with package versions when counts match; else version None.
        for idx, node in enumerate(drmfree_nodes):
            url = node.get("url")
            sha1 = node.get("sha1sum")
            size = node.get("size")
            ver = pkg_versions[idx] if idx < len(pkg_versions) else None
            if url:
                updates.append({
                    "type": "DRM-Free",
                    "version": ver,
                    "url": url,
                    "sha1": sha1,
                    "size_bytes": int(size) if size and size.isdigit() else None,
                    "filename": os.path.basename(url),
                })

    return {"updates": updates}


def fetch_updates_for_disc_id(session: requests.Session, disc_id: str) -> Dict[str, Any]:
    """
    Query Sony's PS3 update endpoint for a given DISC_ID.
    """
    xml_url = f"https://a0.ww.np.dl.playstation.net/tpl/np/{disc_id}/{disc_id}-ver.xml"
    resp = http_get(session, xml_url)
    if not resp or resp.status_code != 200 or not resp.content:
        status = resp.status_code if resp is not None else None
        return {"updates": [], "http_status": status}
    result = parse_ps3_update_xml(resp.content)
    result["http_status"] = 200
    return result


TITLE_ID_RE = __import__("re").compile(r"^[A-Z]{4}[0-9]{5}$")


def is_valid_title_id(s: Optional[str]) -> bool:
    return bool(s) and bool(TITLE_ID_RE.match(s))


def extract_title_ids_from_text(text: str) -> List[str]:
    import re
    if not text:
        return []
    # Extract plausible PS3 title IDs
    ids = re.findall(r"\b([A-Z]{4}[0-9]{5})\b", text.upper())
    # Deduplicate preserving order
    seen: Set[str] = set()
    out: List[str] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def extract_disc_from_fields(entry: Dict[str, Any]) -> Optional[str]:
    """Try to extract a valid title id from FOLDER or TITLE fields."""
    for key in ("FOLDER", "TITLE"):
        val = entry.get(key)
        if not val:
            continue
        for cand in extract_title_ids_from_text(str(val)):
            if is_valid_title_id(cand):
                return cand
    return None


def resolve_disc_id(session: requests.Session, entry: Dict[str, Any], nfo_cache: Dict[str, List[str]]) -> Optional[str]:
    # If DISC_ID already valid, use it
    disc_id = (entry.get("DISC_ID") or "").strip().upper()
    if is_valid_title_id(disc_id):
        return disc_id
    # Try to fetch NFO page and extract IDs
    nfo_url = entry.get("NFO")
    links: List[str] = []
    if nfo_url:
        links.append(nfo_url)
    links.extend([u for u in (entry.get("ROW_LINKS") or []) if u not in links])

    for url in links:
        if url in nfo_cache:
            candidates = nfo_cache[url]
        else:
            resp = http_get(session, url)
            candidates = []
            if resp and resp.status_code == 200:
                candidates = extract_title_ids_from_text(resp.text)
            nfo_cache[url] = candidates
        if candidates:
            return candidates[0]
    return None


def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    })
    session.verify = VERIFY_SSL

    # 1) Scrape renascene pages
    all_rows: List[Dict[str, Any]] = []
    logging.info(f"Scraping renascene across {TOTAL_PAGES} pages...")
    for page in range(1, TOTAL_PAGES + 1):
        rows = parse_renascene_page(session, page)
        logging.info(f"Page {page}: {len(rows)} entries")
        all_rows.extend(rows)
        # small jitter to be polite
        time.sleep(0.2 + random.random() * 0.2)

    logging.info(f"Total entries collected from renascene: {len(all_rows)}")

    # 2) Resolve and validate Title IDs, then group entries by Title ID
    entries_by_disc: Dict[str, List[Dict[str, Any]]] = {}
    nfo_cache: Dict[str, List[str]] = {}
    raw_valid = 0
    resolved_from_fields = 0
    resolved_via_links = 0
    rows_with_links = 0
    for entry in all_rows:
        raw = (entry.get("DISC_ID") or "").strip().upper()
        disc: Optional[str] = None
        if is_valid_title_id(raw):
            disc = raw
        else:
            disc = extract_disc_from_fields(entry)
            if not disc:
                disc = resolve_disc_id(session, entry, nfo_cache)
        if disc and is_valid_title_id(disc):
            if disc == raw:
                raw_valid += 1
            elif disc == extract_disc_from_fields(entry):
                resolved_from_fields += 1
            else:
                resolved_via_links += 1
            entries_by_disc.setdefault(disc, []).append(entry)
        if entry.get("NFO") or entry.get("ROW_LINKS"):
            rows_with_links += 1

    unique_disc_ids = list(entries_by_disc.keys())
    logging.info(
        (
            "Unique valid Title IDs to query updates for: "
            f"{len(unique_disc_ids)} "
            f"(raw: {raw_valid}, fields: {resolved_from_fields}, links: {resolved_via_links}; "
            f"rows with links: {rows_with_links})"
        )
    )

    updates_map: Dict[str, Dict[str, Any]] = {}
    status_counts: Dict[Optional[int], int] = {}
    with futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {executor.submit(fetch_updates_for_disc_id, session, disc): disc for disc in unique_disc_ids}
        for fut in futures.as_completed(future_map):
            disc = future_map[fut]
            try:
                res = fut.result()
                updates_map[disc] = res
                status = res.get("http_status")
                status_counts[status] = status_counts.get(status, 0) + 1
            except Exception as e:
                logging.error(f"Error fetching updates for {disc}: {e}")
                updates_map[disc] = {"updates": []}
                status_counts[None] = status_counts.get(None, 0) + 1

    # 3) Merge updates into entries (duplicate DISC_ID entries all get same updates)
    merged: List[Dict[str, Any]] = []
    for disc, entries in entries_by_disc.items():
        update_info = updates_map.get(disc, {"updates": []})
        for entry in entries:
            enriched = dict(entry)
            enriched["updates"] = update_info.get("updates", [])
            merged.append(enriched)

    # 4) Dedupe exact duplicate records (preserve first occurrence) before writing
    def canonical_key(obj: Dict[str, Any]) -> str:
        try:
            return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        except TypeError:
            def default(o):
                return str(o)
            return json.dumps(obj, sort_keys=True, ensure_ascii=False, default=default, separators=(",", ":"))

    seen: Set[str] = set()
    deduped: List[Dict[str, Any]] = []
    for r in merged:
        k = canonical_key(r)
        if k in seen:
            continue
        seen.add(k)
        deduped.append(r)

    # 5) Save JSON to the same directory as the script
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_FILENAME)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)

    total_updates = sum(len(e.get("updates", [])) for e in deduped)
    logging.info(
        "HTTP status counts: " + ", ".join(
            f"{k if k is not None else 'ERR'}={v}" for k, v in sorted(status_counts.items(), key=lambda x: (x[0] is None, x[0]))
        )
    )
    logging.info(f"Wrote {len(deduped)} records with {total_updates} total updates to {out_path}")


if __name__ == "__main__":
    main()
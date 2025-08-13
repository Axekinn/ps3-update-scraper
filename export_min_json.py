#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Export a minimal JSON with only game name, version, and download URL.

Input: ps3_updates.json (array of objects with 'TITLE'/'FOLDER' and 'updates')
Output: ps3_downloads.json (array of { title, version, url })

Rules:
- Prefer TITLE; fallback to FOLDER; fallback to DISC_ID for the game name.
- Include one entry per available update URL.
- Remove exact duplicates of (title, version, url).
- Preserve first occurrence order.

Usage:
  ./export_min_json.py [input_json] [output_json]
"""

from __future__ import annotations

import sys
import os
import json
from typing import List, Dict, Any, Set, Tuple


def pick_title(entry: Dict[str, Any]) -> str:
    for k in ("TITLE", "FOLDER", "DISC_ID"):
        v = entry.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def export_min(inp_path: str, out_path: str) -> Tuple[int, int]:
    with open(inp_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise SystemExit("Input JSON root must be an array")

    seen: Set[Tuple[str, str, str]] = set()
    out: List[Dict[str, Any]] = []

    for entry in data:
        title = pick_title(entry)
        updates = entry.get("updates") or []
        for up in updates:
            url = (up.get("url") or "").strip()
            version = (up.get("version") or "").strip()
            if not url:
                continue
            key = (title, version, url)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "title": title,
                "version": version or None,
                "url": url,
            })

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    return len(data), len(out)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    inp = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "ps3_updates.json")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, "ps3_downloads.json")

    before_count, out_count = export_min(inp, out)
    print(f"Read {before_count} records; wrote {out_count} minimal download entries to {out}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable
from urllib.parse import quote
import xml.etree.ElementTree as ET


ROOT_SITEMAP_URL = "https://www.classcentral.com/sitemap.xml"
OUTPUT_PATH = Path("/code/data/all-links-classcentral")
USER_AGENT = "Mozilla/5.0 (compatible; Codex sitemap fetcher)"
CDX_API = "https://web.archive.org/cdx/search/cdx"


def http_get(url: str, timeout: int = 60, retries: int = 5, pause: float = 1.5) -> str:
    command = [
        "curl",
        "-fsSL",
        "--retry",
        str(retries),
        "--retry-all-errors",
        "--connect-timeout",
        str(timeout),
        "--max-time",
        str(timeout),
        "-A",
        USER_AGENT,
        url,
    ]
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return subprocess.check_output(command, text=True)
        except subprocess.CalledProcessError as exc:
            last_error = exc
            if attempt == retries:
                break
            time.sleep(pause * attempt)
    raise RuntimeError(f"request failed for {url}: {last_error}") from last_error


def get_latest_snapshot(original_url: str) -> str:
    query = (
        f"{CDX_API}?url={quote(original_url, safe='')}"
        "&output=json&fl=timestamp,original,statuscode"
        "&filter=statuscode:200&limit=1&from=2024"
    )
    payload = json.loads(http_get(query, timeout=30))
    if len(payload) < 2:
        raise RuntimeError(f"no archive snapshot found for {original_url}")
    return payload[1][0]


def archive_raw_url(original_url: str, timestamp: str) -> str:
    return f"https://web.archive.org/web/{timestamp}id_/{original_url}"


def parse_locs(xml_text: str) -> list[str]:
    root = ET.fromstring(xml_text)
    return [
        node.text.strip()
        for node in root.iter()
        if node.tag.endswith("loc") and node.text and node.text.strip()
    ]


def unique_in_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def fetch_sitemap_urls(sitemap_url: str, preferred_timestamp: str) -> list[str]:
    errors = []
    for timestamp in unique_in_order([preferred_timestamp, get_latest_snapshot(sitemap_url)]):
        try:
            return parse_locs(http_get(archive_raw_url(sitemap_url, timestamp)))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{timestamp}: {exc}")
            time.sleep(1)
    raise RuntimeError("; ".join(errors))


def main() -> int:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    root_timestamp = get_latest_snapshot(ROOT_SITEMAP_URL)
    root_urls = fetch_sitemap_urls(ROOT_SITEMAP_URL, root_timestamp)

    all_links: list[str] = []
    seen: set[str] = set()

    for index, sitemap_url in enumerate(root_urls, start=1):
        try:
            page_urls = fetch_sitemap_urls(sitemap_url, root_timestamp)
        except Exception as exc:  # noqa: BLE001
            print(f"FAILED {sitemap_url}: {exc}", file=sys.stderr)
            continue

        for url in page_urls:
            if url in seen:
                continue
            seen.add(url)
            all_links.append(url)

        print(
            f"processed {index}/{len(root_urls)} sitemaps, {len(all_links)} links",
            file=sys.stderr,
        )
        time.sleep(0.5)

    OUTPUT_PATH.write_text("".join(f"{url}\n" for url in all_links), encoding="utf-8")
    print(f"wrote {len(all_links)} links to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

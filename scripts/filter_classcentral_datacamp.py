#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


INPUT_PATH = Path("/code/data/all-links-classcentral")
OUTPUT_PATH = Path("/code/data/datacamp-course-links-classcentral")


def main() -> int:
    urls = INPUT_PATH.read_text(encoding="utf-8").splitlines()
    matches = [
        url for url in urls if "/course/" in url and "datacamp" in url.lower()
    ]
    OUTPUT_PATH.write_text("".join(f"{url}\n" for url in matches), encoding="utf-8")
    print(f"wrote {len(matches)} datacamp course urls to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Compare the original WP sitemap URLs with files produced by `jekyll build`."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
URLS = Path(__file__).resolve().parent / "urls.txt"
EXCLUDED = Path(__file__).resolve().parent / "excluded-patreon.txt"
REPORT = Path(__file__).resolve().parent / "url-verification.json"

DROP_PREFIXES = {
    "/clients/",
    "/mailinglist/",
    "/register/",
    "/members/",
    "/activity/",
    "/groups/",
    "/chatroom/",
    "/activate/",
}


def site_file_for(path: str) -> Path | None:
    path = unquote(path)
    if not path.startswith("/"):
        path = "/" + path
    if path == "/":
        candidates = [SITE / "index.html"]
    else:
        rel = path.strip("/")
        candidates = [
            SITE / rel / "index.html",
            SITE / f"{rel}.html",
            SITE / rel,
        ]
    for cand in candidates:
        if cand.exists():
            return cand
    return None


def main() -> int:
    urls = [u.strip() for u in URLS.read_text(encoding="utf-8").splitlines() if u.strip()]
    excluded = set()
    if EXCLUDED.exists():
        excluded = {line.strip() for line in EXCLUDED.read_text(encoding="utf-8").splitlines() if line.strip()}

    resolved = []
    missing = []
    for url in urls:
        parsed = urlparse(url)
        path = unquote(parsed.path) or "/"
        if not path.endswith("/") and path != "/":
            path = path + "/"
        slug = path.strip("/")
        first = slug.split("/")[0] if slug else ""
        reason = None
        found = site_file_for(path)
        if found:
            resolved.append({"url": url, "path": path, "file": str(found.relative_to(ROOT))})
            continue
        if first in excluded and "/" not in slug:
            reason = "excluded-patreon"
        elif path in DROP_PREFIXES:
            reason = "dropped-page-should-redirect"
        elif path.startswith("/type/"):
            reason = "wp-post-format-archive-not-migrated"
        elif path.startswith("/category/"):
            reason = "category-archive-empty-or-unused-after-patreon-filter"
        elif path.startswith("/tag/"):
            reason = "tag-archive-empty-or-unused-after-patreon-filter"
        else:
            reason = "not-built"
        missing.append({"url": url, "path": path, "reason": reason})

    report = {
        "sitemap_urls": len(urls),
        "resolved": len(resolved),
        "unresolved": len(missing),
        "unresolved_by_reason": {},
        "missing": missing,
    }
    for item in missing:
        report["unresolved_by_reason"][item["reason"]] = report["unresolved_by_reason"].get(item["reason"], 0) + 1
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"urls={len(urls)} resolved={len(resolved)} unresolved={len(missing)}")
    for reason, count in sorted(report["unresolved_by_reason"].items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {count:4d}  {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

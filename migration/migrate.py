#!/usr/bin/env python3
"""Migrate public apostolos.bg WordPress content into this Jekyll site.

Uses only the unauthenticated REST API so gated Patreon posts stay gated:
the API returns the public teaser/unlock banner, and those posts are dropped
entirely (no teaser is published).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlparse, urlunparse

import requests
import yaml
from bs4 import BeautifulSoup, NavigableString
from markdownify import markdownify as html_to_md

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = Path(__file__).resolve().parent / "raw"
POSTS_DIR = ROOT / "_posts"
PAGES_DIR = ROOT / "_pages"
UPLOADS_DIR = ROOT / "assets" / "uploads"
IMAGES_DIR = ROOT / "assets" / "images"
EXCLUDED_FILE = Path(__file__).resolve().parent / "excluded-patreon.txt"
REPORT_FILE = Path(__file__).resolve().parent / "report.json"
MEDIA_MANIFEST = Path(__file__).resolve().parent / "media-manifest.json"

API = "https://apostolos.bg/wp-json/wp/v2"
SITE = "https://apostolos.bg"
USER_AGENT = "apostolos-migration/1.0 (+https://github.com/oneinterweb/apostolos)"

PATREON_MARKERS = (
    "patreon-campaign-banner",
    "patreon-locked-content-message",
    "patreon-unlock-post",
    "patreon-patron-button-wrapper",
    "Unlock with Patreon",
)

DROP_PAGE_SLUGS = {
    "clients",
    "mailinglist",
    "register",
    "members",
    "activity",
    "groups",
    "chatroom",
    "activate",
}

CONTACT_PAGE_SLUGS = {"contact", "contact-2", "about"}

AUTHOR_MAP = {
    1: "admin",
    2: "Георги Бакалов",
    3: "danielatrifonowa",
}

# Browser-like headers: Cloudflare challenges HTML and hotlink-style
# fetches that use a custom UA, but REST + image GETs succeed with this.
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": BROWSER_UA,
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "bg-BG,bg;q=0.9,en;q=0.8",
        "Referer": "https://apostolos.bg/",
    }
)
MEDIA_HEADERS = {
    "User-Agent": BROWSER_UA,
    "Accept": "image/jpeg,image/png,image/gif,image/svg+xml,audio/mpeg,application/pdf,*/*;q=0.2",
    "Accept-Language": "bg-BG,bg;q=0.9,en;q=0.8",
    "Referer": "https://apostolos.bg/",
}


def log(msg: str) -> None:
    print(msg, flush=True)


def wp_get(path: str, params: dict[str, Any] | None = None, retries: int = 5) -> requests.Response:
    url = path if path.startswith("http") else f"{API}/{path.lstrip('/')}"
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            r = SESSION.get(url, params=params, timeout=60)
            if r.status_code in (429, 502, 503, 504):
                time.sleep(1.5 * (attempt + 1))
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as exc:
            last_err = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"GET failed {url}: {last_err}")


def fetch_all(endpoint: str, extra: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page = 1
    extra = extra or {}
    while True:
        params = {"per_page": 100, "page": page, **extra}
        r = wp_get(endpoint, params)
        batch = r.json()
        if not isinstance(batch, list):
            raise RuntimeError(f"Unexpected payload from {endpoint}: {batch!r}")
        items.extend(batch)
        total_pages = int(r.headers.get("X-WP-TotalPages", "1"))
        log(f"  {endpoint} page {page}/{total_pages} (+{len(batch)}, total {len(items)})")
        if page >= total_pages or not batch:
            break
        page += 1
        time.sleep(0.15)
    return items


def decode_slug(slug: str) -> str:
    if not slug:
        return slug
    return unquote(slug).strip("/")


def is_patreon_locked(html: str) -> bool:
    if not html:
        return False
    lower = html
    return any(marker in lower for marker in PATREON_MARKERS)


def strip_tags(html: str) -> str:
    text = BeautifulSoup(html or "", "lxml").get_text(" ", strip=True)
    return unescape(text)


def clean_title(html: str) -> str:
    return unescape(BeautifulSoup(html or "", "lxml").get_text("", strip=True))


def yaml_str(value: Any) -> str:
    dumped = yaml.safe_dump(value, allow_unicode=True, default_flow_style=True).strip()
    if dumped.endswith("\n..."):
        dumped = dumped[:-4].strip()
    return dumped


def fm_quote(value: str) -> str:
    return yaml.safe_dump(value, allow_unicode=True, default_style='"').strip()


THUMB_RE = re.compile(r"-(\d+)x(\d+)(?=\.[A-Za-z0-9]+$)")
SCALED_RE = re.compile(r"-scaled(?=\.[A-Za-z0-9]+$)")
CONTACT_FORM_RE = re.compile(
    r"\[contact-form[^\]]*\].*?\[/contact-form\]",
    re.I | re.S,
)
WP_COMMENT_RE = re.compile(r"<!--\s*/?wp:.*?-->", re.S)
UPLOAD_HOSTS = (
    "apostolos.bg",
    "www.apostolos.bg",
    "new.apostolos.bg",
    "georgebakalov.bg",
    "www.georgebakalov.bg",
)


def original_upload_path(url: str) -> str | None:
    """Return wp-content/uploads relative path for an original-size file, or None."""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    marker = "/wp-content/uploads/"
    if marker not in path:
        return None
    rel = path.split(marker, 1)[1]
    rel = THUMB_RE.sub("", rel)
    # Keep -scaled files only when that is what WP served as the "full" size;
    # prefer the unscaled name first, download_media will fall back.
    return rel.lstrip("/")


def rewrite_upload_href(url: str) -> str | None:
    rel = original_upload_path(url)
    if not rel:
        return None
    rel = SCALED_RE.sub("", rel)
    return "@@BASEURL@@/assets/uploads/" + rel


def rewrite_site_href(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host not in {"apostolos.bg", "new.apostolos.bg", "georgebakalov.bg"} and host != "":
        return None
    path = unquote(parsed.path or "/")
    if "/wp-content/uploads/" in path:
        return rewrite_upload_href(url)
    if "/wp-content/" in path or "/wp-json/" in path or "/patreon-flow/" in path:
        return None
    parts = [p for p in path.split("/") if p]
    # Drop leftover date permalink prefixes /YYYY/MM/DD/slug/
    if len(parts) >= 4 and parts[0].isdigit() and len(parts[0]) == 4 and parts[1].isdigit() and parts[2].isdigit():
        parts = parts[3:]
    new_path = "/" + "/".join(parts)
    last = parts[-1] if parts else ""
    if new_path != "/" and not new_path.endswith("/") and "." not in last:
        new_path = new_path.rstrip("/") + "/"
    if new_path == "//" or new_path == "/":
        new_path = "/"
    return "@@BASEURL@@" + new_path


def collect_media_urls(html: str) -> set[str]:
    urls: set[str] = set()
    if not html:
        return urls
    soup = BeautifulSoup(html, "lxml")
    for tag, attr in (("img", "src"), ("img", "data-src"), ("a", "href"), ("source", "src"), ("audio", "src")):
        for el in soup.find_all(tag):
            val = el.get(attr)
            if val:
                urls.add(val)
    for el in soup.find_all(srcset=True):
        for part in el["srcset"].split(","):
            u = part.strip().split(" ")[0]
            if u:
                urls.add(u)
    for match in re.findall(r"https?://[^\s\"'<>]+wp-content/uploads/[^\s\"'<>]+", html):
        urls.add(match)
    return urls


def protect_embeds(html: str) -> tuple[str, dict[str, str]]:
    """Replace iframes / video figures with placeholders so markdownify keeps them."""
    soup = BeautifulSoup(html, "lxml")
    placeholders: dict[str, str] = {}
    idx = 0
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src") or ""
        title = iframe.get("title") or "embed"
        wrapper = (
            f'<div class="responsive-embed">'
            f'<iframe src="{src}" title="{title}" allowfullscreen loading="lazy"></iframe>'
            f"</div>"
        )
        key = f"EMBEDPLACEHOLDER{idx}XYZ"
        placeholders[key] = wrapper
        iframe.replace_with(NavigableString(key))
        idx += 1
    return str(soup), placeholders


def replace_contact_forms(html: str) -> str:
    html = CONTACT_FORM_RE.sub("<!--CONTACT_FORM-->", html)
    if "<!--CONTACT_FORM-->" not in html and re.search(r"\[contact-field", html, re.I):
        html = re.sub(r"\[contact-form[^\]]*", "<!--CONTACT_FORM-->", html, flags=re.I)
        html = re.sub(r"\[/?contact-field[^\]]*\]", "", html, flags=re.I)
        html = re.sub(r"\[/contact-form\]", "", html, flags=re.I)
    return html


def rewrite_html_urls(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["a", "img", "source", "audio", "video"]):
        for attr in ("href", "src"):
            val = tag.get(attr)
            if not val:
                continue
            rewritten = rewrite_site_href(val) or rewrite_upload_href(val)
            if rewritten:
                tag[attr] = rewritten
        if tag.has_attr("srcset"):
            del tag["srcset"]
        for attr in ("srcset", "data-srcset", "sizes", "data-src"):
            if tag.has_attr(attr) and attr != "src":
                if attr == "data-src" and not tag.get("src"):
                    rewritten = rewrite_upload_href(tag[attr])
                    if rewritten:
                        tag["src"] = rewritten
                if attr != "src":
                    del tag[attr]
    return str(soup)


def html_to_markdown(html: str) -> str:
    html = WP_COMMENT_RE.sub("", html or "")
    html = replace_contact_forms(html)
    html = rewrite_html_urls(html)
    html, embeds = protect_embeds(html)
    md = html_to_md(
        html,
        heading_style="ATX",
        bullets="-",
        strip=["script", "style"],
        escape_underscores=False,
        escape_asterisks=False,
    )
    for key, embed in embeds.items():
        md = md.replace(key, "\n\n" + embed + "\n\n")
    md = md.replace("<!--CONTACT_FORM-->", "\n\n@@CONTACT_FORM@@\n\n")
    # Escape leftover Liquid from WP content, then restore our own tags.
    md = md.replace("{{", "{{ '{{' }}").replace("{%", "{{ '{%' }}")
    md = md.replace("@@BASEURL@@", "{{ site.baseurl }}")
    md = md.replace("@@CONTACT_FORM@@", "{% include contact-form.html %}")
    md = convert_youtube_shortcodes(md)
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
    return md


YOUTUBE_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{6,})"
)
YOUTUBE_SHORTCODE_RE = re.compile(
    r"\[(?:youtube|embed)(?:\s+|\]\()?(https?://[^\s\]\)]+)(?:\)|\])?",
    re.I,
)


def youtube_iframe(url: str) -> str | None:
    m = YOUTUBE_ID_RE.search(url)
    if not m:
        return None
    vid = m.group(1)
    return (
        '<div class="responsive-embed">'
        f'<iframe src="https://www.youtube.com/embed/{vid}" '
        'title="YouTube" allowfullscreen loading="lazy"></iframe>'
        "</div>"
    )


def convert_youtube_shortcodes(md: str) -> str:
    def repl(match: re.Match) -> str:
        iframe = youtube_iframe(match.group(1))
        return iframe or match.group(0)

    md = YOUTUBE_SHORTCODE_RE.sub(repl, md)
    return md


def safe_filename(slug: str, fallback: str) -> str:
    slug = slug.strip().replace("/", "-")
    slug = re.sub(r"[^\w\-.\u0400-\u04FF]+", "-", slug, flags=re.UNICODE)
    slug = slug.strip("-.") or fallback
    return slug[:180]


def write_front_matter(data: dict[str, Any], body: str) -> str:
    # Keep control of key order and Unicode
    lines = ["---"]
    for key, value in data.items():
        if value is None or value == "" or value == []:
            continue
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        elif isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {fm_quote(str(item)) if isinstance(item, str) else item}")
        elif isinstance(value, dict):
            lines.append(f"{key}:")
            dumped = yaml.safe_dump(value, allow_unicode=True, default_flow_style=False).strip()
            for row in dumped.splitlines():
                lines.append(f"  {row}")
        else:
            lines.append(f"{key}: {fm_quote(str(value))}")
    lines.append("---")
    lines.append("")
    lines.append(body.lstrip("\n"))
    if not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    return "\n".join(lines) if not lines[0].startswith("---\n") else "\n".join(lines)


def load_or_fetch(name: str, fetcher, refresh: bool) -> Any:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{name}.json"
    if path.exists() and not refresh:
        log(f"cache hit {path}")
        return json.loads(path.read_text(encoding="utf-8"))
    data = fetcher()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def taxonomy_map(items: list[dict[str, Any]]) -> dict[int, dict[str, str]]:
    out: dict[int, dict[str, str]] = {}
    for item in items:
        out[item["id"]] = {
            "slug": decode_slug(item.get("slug") or ""),
            "name": unescape(item.get("name") or ""),
        }
    return out


def featured_url(post: dict[str, Any], media_by_id: dict[int, dict[str, Any]]) -> str | None:
    mid = post.get("featured_media") or 0
    if mid and mid in media_by_id:
        return media_by_id[mid].get("source_url")
    return post.get("jetpack_featured_media_url") or None


def local_upload_from_url(url: str) -> str | None:
    rel = original_upload_path(url)
    if not rel:
        return None
    rel = SCALED_RE.sub("", rel)
    return "/assets/uploads/" + rel


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def download_one(url: str, dest: Path) -> tuple[str, int, str | None]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 500:
        return str(dest.relative_to(ROOT)), dest.stat().st_size, None
    parsed = urlparse(url)
    path = parsed.path
    ext = os.path.splitext(path)[1].lower()
    candidates = [url]
    if ext in IMAGE_EXTS and not SCALED_RE.search(path):
        stem, extension = os.path.splitext(path)
        candidates.append(urlunparse(parsed._replace(path=f"{stem}-scaled{extension}")))
    last_err = None
    for candidate in candidates:
        try:
            r = SESSION.get(
                candidate,
                timeout=90,
                stream=True,
                allow_redirects=True,
                headers=MEDIA_HEADERS,
            )
            if r.status_code == 404:
                last_err = f"404 {candidate}"
                continue
            if r.status_code == 403:
                last_err = f"403 {candidate}"
                continue
            r.raise_for_status()
            ctype = (r.headers.get("Content-Type") or "").lower()
            if "text/html" in ctype:
                last_err = f"html challenge {candidate}"
                continue
            tmp = dest.with_suffix(dest.suffix + ".part")
            size = 0
            with tmp.open("wb") as fh:
                for chunk in r.iter_content(64 * 1024):
                    if chunk:
                        fh.write(chunk)
                        size += len(chunk)
            if size < 32:
                tmp.unlink(missing_ok=True)
                last_err = f"tiny body {candidate}"
                continue
            tmp.replace(dest)
            return str(dest.relative_to(ROOT)), size, None
        except requests.RequestException as exc:
            last_err = str(exc)
    return str(dest), 0, last_err


def download_media(urls: set[str]) -> list[dict[str, Any]]:
    jobs: list[tuple[str, Path]] = []
    seen_rel: set[str] = set()
    for url in sorted(urls):
        if not url or url.startswith("data:"):
            continue
        abs_url = urljoin(SITE + "/", url)
        host = urlparse(abs_url).netloc.lower().lstrip("www.")
        if host not in UPLOAD_HOSTS and "wp-content/uploads" not in abs_url:
            continue
        rel = original_upload_path(abs_url)
        if not rel:
            continue
        rel = SCALED_RE.sub("", rel)
        if rel in seen_rel:
            continue
        seen_rel.add(rel)
        dest = UPLOADS_DIR / rel
        # Always fetch from apostolos.bg (new. and georgebakalov. redirect/legacy)
        parsed = urlparse(abs_url)
        fetch_url = urlunparse(parsed._replace(scheme="https", netloc="apostolos.bg", path="/wp-content/uploads/" + rel))
        jobs.append((fetch_url, dest))

    log(f"Downloading {len(jobs)} original media files…")
    results: list[dict[str, Any]] = []
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {pool.submit(download_one, url, dest): (url, dest) for url, dest in jobs}
        for i, fut in enumerate(as_completed(futs), 1):
            url, dest = futs[fut]
            rel, size, err = fut.result()
            results.append({"url": url, "path": rel, "bytes": size, "error": err})
            if i % 25 == 0 or err:
                log(f"  media {i}/{len(jobs)} {rel} {size} {err or 'ok'}")
    return results


def convert_post(
    post: dict[str, Any],
    cats: dict[int, dict[str, str]],
    tags: dict[int, dict[str, str]],
    media_by_id: dict[int, dict[str, Any]],
) -> tuple[Path, set[str]]:
    slug = decode_slug(post.get("slug") or "") or f"post-{post['id']}"
    title = clean_title(post.get("title", {}).get("rendered", ""))
    html = post.get("content", {}).get("rendered", "") or ""
    excerpt = strip_tags(post.get("excerpt", {}).get("rendered", "") or "")
    excerpt = CONTACT_FORM_RE.sub("", excerpt)
    excerpt = re.sub(r"\[(?:youtube|embed)[^\]]*\]", "", excerpt, flags=re.I)
    excerpt = re.sub(r"\s+", " ", excerpt).strip()
    date = post.get("date") or post.get("date_gmt")
    # WP date is local Europe/Sofia already
    date_prefix = (date or "1970-01-01")[:10]
    categories = [cats[i]["slug"] for i in post.get("categories") or [] if i in cats and cats[i]["slug"]]
    tag_slugs = [tags[i]["slug"] for i in post.get("tags") or [] if i in tags and tags[i]["slug"]]
    author = AUTHOR_MAP.get(post.get("author"), "Георги Бакалов")
    feat = featured_url(post, media_by_id)
    media_urls = collect_media_urls(html)
    if feat:
        media_urls.add(feat)
    body = html_to_markdown(html)
    fm: dict[str, Any] = {
        "title": title,
        "date": date,
        "last_modified_at": post.get("modified") or date,
        "permalink": f"/{slug}/",
        "slug": slug,
        "author": author,
        "excerpt": excerpt,
        "categories": categories,
        "tags": tag_slugs,
        "wp_id": post["id"],
        "comments": False,
    }
    local_feat = local_upload_from_url(feat) if feat else None
    if local_feat:
        fm["header"] = {"teaser": local_feat}
        fm["image"] = local_feat
    filename = f"{date_prefix}-{safe_filename(slug, str(post['id']))}.md"
    path = POSTS_DIR / filename
    path.write_text(write_front_matter(fm, body), encoding="utf-8")
    return path, media_urls


def convert_page(page: dict[str, Any], media_by_id: dict[int, dict[str, Any]]) -> tuple[Path, set[str]]:
    slug = decode_slug(page.get("slug") or "") or f"page-{page['id']}"
    title = clean_title(page.get("title", {}).get("rendered", ""))
    html = page.get("content", {}).get("rendered", "") or ""
    excerpt = strip_tags(page.get("excerpt", {}).get("rendered", "") or "")
    excerpt = CONTACT_FORM_RE.sub("", excerpt)
    excerpt = re.sub(r"\[(?:youtube|embed)[^\]]*\]", "", excerpt, flags=re.I)
    excerpt = re.sub(r"\s+", " ", excerpt).strip()
    date = page.get("date")
    feat = featured_url(page, media_by_id)
    media_urls = collect_media_urls(html)
    if feat:
        media_urls.add(feat)
    body = html_to_markdown(html)
    if slug in CONTACT_PAGE_SLUGS and "include contact-form.html" not in body:
        body = body.rstrip() + "\n\n{% include contact-form.html %}\n"
    fm: dict[str, Any] = {
        "title": title or slug,
        "permalink": f"/{slug}/",
        "slug": slug,
        "layout": "single",
        "author_profile": False,
        "comments": False,
        "wp_id": page["id"],
    }
    if date:
        fm["date"] = date
    if excerpt:
        fm["excerpt"] = excerpt
    local_feat = local_upload_from_url(feat) if feat else None
    if local_feat:
        fm["header"] = {"teaser": local_feat}
        fm["image"] = local_feat
    filename = f"{safe_filename(slug, str(page['id']))}.md"
    path = PAGES_DIR / filename
    path.write_text(write_front_matter(fm, body), encoding="utf-8")
    return path, media_urls


def reset_generated() -> None:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    keep_pages = {"search.md", "year-archive.md"}
    for path in POSTS_DIR.glob("*.md"):
        path.unlink()
    for path in PAGES_DIR.glob("*.md"):
        if path.name not in keep_pages:
            path.unlink()


def maybe_fetch_logo(media_items: list[dict[str, Any]]) -> None:
    """Keep the hand-made SVG avatar; do not overwrite it with random WP images."""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    dest = IMAGES_DIR / "logo.svg"
    if dest.exists() and dest.stat().st_size > 0:
        return
    dest.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">'
        '<rect width="128" height="128" rx="12" fill="#1a365d"/>'
        '<text x="64" y="84" text-anchor="middle" font-size="64" fill="#fff" '
        'font-family="Georgia, serif">А</text></svg>\n',
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-api", action="store_true", help="Re-download REST JSON")
    parser.add_argument("--from-cache", action="store_true", help="Use migration/raw JSON only")
    parser.add_argument("--skip-media", action="store_true")
    args = parser.parse_args()
    refresh = args.refresh_api and not args.from_cache
    if args.from_cache:
        refresh = False

    log("Fetching WordPress public REST data…")
    posts = load_or_fetch("posts", lambda: fetch_all("posts", {"status": "publish"}), refresh)
    pages = load_or_fetch("pages", lambda: fetch_all("pages", {"status": "publish"}), refresh)
    categories = load_or_fetch("categories", lambda: fetch_all("categories"), refresh)
    tags = load_or_fetch("tags", lambda: fetch_all("tags"), refresh)
    media_items = load_or_fetch("media", lambda: fetch_all("media"), refresh)

    cats = taxonomy_map(categories)
    tag_map = taxonomy_map(tags)
    media_by_id = {m["id"]: m for m in media_items}

    locked = []
    public_posts = []
    leaked = []
    for post in posts:
        html = post.get("content", {}).get("rendered", "") or ""
        slug = decode_slug(post.get("slug") or "") or str(post["id"])
        if is_patreon_locked(html):
            locked.append(post)
            # If the banner is short and there is no long article body beside it,
            # REST is not leaking full text. Flag unusually long "locked" bodies.
            banner_only = "patreon-campaign-banner" in html
            text_len = len(strip_tags(html))
            if banner_only and text_len > 1200:
                leaked.append({"id": post["id"], "slug": slug, "text_len": text_len})
        else:
            public_posts.append(post)

    locked_slugs = []
    for post in locked:
        slug = decode_slug(post.get("slug") or "") or str(post["id"])
        locked_slugs.append(slug)
    locked_slugs = sorted(set(locked_slugs))
    EXCLUDED_FILE.write_text("\n".join(locked_slugs) + "\n", encoding="utf-8")
    log(f"Posts: {len(posts)} published, {len(locked)} Patreon-locked excluded, {len(public_posts)} migrated")
    if leaked:
        log(f"WARNING: {len(leaked)} locked posts have unusually long public REST text")

    drop_pages = []
    keep_pages = []
    for page in pages:
        slug = decode_slug(page.get("slug") or "")
        if slug in DROP_PAGE_SLUGS:
            drop_pages.append(slug)
        else:
            keep_pages.append(page)
    log(f"Pages: {len(pages)} published, {len(drop_pages)} dropped, {len(keep_pages)} migrated")

    reset_generated()
    media_urls: set[str] = set()
    written_posts = []
    for post in public_posts:
        path, urls = convert_post(post, cats, tag_map, media_by_id)
        written_posts.append(str(path.relative_to(ROOT)))
        media_urls |= urls
    written_pages = []
    for page in keep_pages:
        path, urls = convert_page(page, media_by_id)
        written_pages.append(str(path.relative_to(ROOT)))
        media_urls |= urls

    maybe_fetch_logo(media_items)

    media_results: list[dict[str, Any]] = []
    if not args.skip_media:
        media_results = download_media(media_urls)
        MEDIA_MANIFEST.write_text(json.dumps(media_results, ensure_ascii=False, indent=2), encoding="utf-8")

    ok_media = [m for m in media_results if not m.get("error") and m.get("bytes", 0) > 0]
    failed_media = [m for m in media_results if m.get("error")]
    total_bytes = sum(m.get("bytes") or 0 for m in ok_media)

    report = {
        "source": SITE,
        "published_posts_api": len(posts),
        "excluded_patreon": len(locked),
        "migrated_posts": len(public_posts),
        "published_pages_api": len(pages),
        "dropped_pages": sorted(drop_pages),
        "migrated_pages": len(keep_pages),
        "media_files": len(ok_media),
        "media_bytes": total_bytes,
        "media_failed": failed_media,
        "patreon_rest_leak_suspects": leaked,
        "patreon_detection": {
            "markers": list(PATREON_MARKERS),
            "note": (
                "Unauthenticated REST returns the public Patreon banner for locked "
                "posts, not the patron-only body. Locked posts are omitted entirely."
            ),
        },
        "written_posts": written_posts,
        "written_pages": written_pages,
    }
    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log(
        f"Done. posts={len(public_posts)} pages={len(keep_pages)} "
        f"excluded_patreon={len(locked)} media={len(ok_media)} "
        f"({total_bytes/1_000_000:.1f} MB) failed_media={len(failed_media)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

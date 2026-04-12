from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse


def normalize_url(base_url: str, href: str) -> str | None:
    if not href:
        return None
    absolute = urljoin(base_url, href.strip())
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"}:
        return None
    clean = parsed._replace(fragment="", query="")
    normalized = urlunparse(clean)
    return canonicalize_url(normalized)


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    clean = parsed._replace(path=path, fragment="", query="")
    return urlunparse(clean)


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "index"


def path_from_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    return path or "index"


def output_path_for_url(output_dir: Path, url: str) -> Path:
    raw_path = path_from_url(url)
    parts = [slugify(part) for part in raw_path.split("/") if part]
    if not parts:
        parts = ["index"]
    return output_dir.joinpath(*parts).with_suffix(".md")


def collapse_blank_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

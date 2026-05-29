from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import parse_qsl, quote_plus, urljoin, urlparse, urlunparse, unquote_plus


DEFAULT_STRIP_QUERY_PARAMS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "mkt_tok",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


def normalize_url(
    base_url: str,
    href: str,
    *,
    strip_query_params: set[str] | None = None,
) -> str | None:
    if not href:
        return None
    absolute = urljoin(base_url, href.strip())
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"}:
        return None
    clean = parsed._replace(fragment="")
    normalized = urlunparse(clean)
    return canonicalize_url(normalized, strip_query_params=strip_query_params)


def canonicalize_url(
    url: str,
    *,
    strip_query_params: set[str] | None = None,
) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    query = _canonicalize_query(parsed.query, strip_query_params=strip_query_params)
    clean = parsed._replace(path=path, fragment="", query=query)
    return urlunparse(clean)


def site_origin(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "index"


def path_from_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    return path or "index"


def output_path_for_url(output_dir: Path, url: str) -> Path:
    parts = _url_identity_parts(url)
    if not parts:
        parts = ["index"]
    return output_dir.joinpath(*parts).with_suffix(".md")


def collapse_blank_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def short_hash(text: str, length: int = 10) -> str:
    return stable_hash(text)[:length]


def source_path_for_url(url: str) -> str:
    return "/".join(_url_identity_parts(url))


def looks_like_xml(url: str, body: str) -> bool:
    lowered_url = url.lower()
    if any(token in lowered_url for token in (".xml", ".wsdl", "?wsdl")):
        return True

    stripped = body.lstrip()
    prefix = stripped[:200].lower()
    return prefix.startswith("<?xml") or prefix.startswith("<wsdl:") or prefix.startswith("<definitions")


def _canonicalize_query(query: str, *, strip_query_params: set[str] | None = None) -> str:
    if not query:
        return ""

    blocked = {item.lower() for item in (strip_query_params or DEFAULT_STRIP_QUERY_PARAMS)}
    items = _parse_query_items(query)
    filtered = [
        item
        for item in items
        if item[0].lower() not in blocked
    ]
    if not filtered:
        return ""

    filtered.sort(key=lambda item: (item[0].lower(), item[1], item[2]))
    pieces: list[str] = []
    for key, value, is_pair in filtered:
        encoded_key = quote_plus(key)
        if is_pair:
            pieces.append(f"{encoded_key}={quote_plus(value)}")
        else:
            pieces.append(encoded_key)
    return "&".join(pieces)


def _query_identity_parts(url: str) -> list[str]:
    parsed = urlparse(url)
    if not parsed.query:
        return []

    items = _parse_query_items(parsed.query)
    if not items:
        return [f"query-{short_hash(parsed.query)}"]

    parts: list[str] = []
    for key, value, is_pair in items:
        if is_pair:
            if value:
                parts.append(f"{slugify(key)}-{slugify(value)}")
            else:
                parts.append(slugify(key))
        else:
            parts.append(slugify(key))

    compact = "-".join(parts)
    if len(compact) > 96:
        return [f"query-{short_hash(parsed.query)}"]
    return [compact]


def _url_identity_parts(url: str) -> list[str]:
    raw_path = path_from_url(url)
    parts = [slugify(part) for part in raw_path.split("/") if part]
    parts.extend(_query_identity_parts(url))
    return parts


def _parse_query_items(query: str) -> list[tuple[str, str, bool]]:
    items: list[tuple[str, str, bool]] = []
    for raw_item in query.split("&"):
        if not raw_item:
            continue
        if "=" in raw_item:
            key, value = raw_item.split("=", 1)
            items.append((unquote_plus(key), unquote_plus(value), True))
        else:
            items.append((unquote_plus(raw_item), "", False))
    return items

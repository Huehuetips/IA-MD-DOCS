from __future__ import annotations

import heapq
import logging
import warnings
from xml.etree import ElementTree as ET
from urllib.parse import urlparse

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import requests

from .models import DiscoveredPage, PipelineConfig
from .utils import canonicalize_url, looks_like_xml, normalize_url


logger = logging.getLogger(__name__)


class DocumentationCrawler:
    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = config.user_agent

    def discover(self) -> list[DiscoveredPage]:
        logger.info(
            "Crawler iniciado domain=%s include_prefixes=%s exclude_paths=%s max_visits=%s",
            self.config.domain,
            self.config.include_prefixes or ["<all>"],
            self.config.exclude_paths or ["<none>"],
            self.config.max_visits,
        )
        queue: list[tuple[int, int, DiscoveredPage]] = []
        counter = 0
        sitemap_urls = self._discover_sitemap_urls()
        logger.info("Sitemaps detectados=%s", len(sitemap_urls))
        for sitemap_url in sitemap_urls:
            discovered_urls = self._read_sitemap(sitemap_url)
            logger.info("Sitemap procesado url=%s urls=%s", sitemap_url, len(discovered_urls))
            for discovered_url in discovered_urls:
                if self._should_visit(discovered_url):
                    counter += 1
                    heapq.heappush(
                        queue,
                        (
                            self._priority(discovered_url, 1),
                            counter,
                            DiscoveredPage(discovered_url, 1),
                        ),
                    )
        heapq.heappush(
            queue,
            (self._priority(self.config.root_url, 0), counter, DiscoveredPage(self.config.root_url, 0)),
        )
        seen: set[str] = set()
        visited: list[DiscoveredPage] = []

        while queue and len(visited) < self.config.max_visits:
            _, _, page = heapq.heappop(queue)
            if page.url in seen or not self._should_visit(page.url):
                continue

            seen.add(page.url)
            visited.append(page)
            logger.info(
                "Descubriendo pagina %s/%s depth=%s queue=%s url=%s",
                len(visited),
                self.config.max_visits,
                page.depth,
                len(queue),
                page.url,
            )

            html = self._fetch_html(page.url)
            if not html:
                continue

            if looks_like_xml(page.url, html):
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
                    soup = BeautifulSoup(html, "html.parser")
            else:
                soup = BeautifulSoup(html, "html.parser")
            for node in soup.select("a[href], link[href], area[href], form[action]"):
                href = node.get("action") if node.name == "form" else node.get("href")
                normalized = normalize_url(page.url, href)
                if not normalized or normalized in seen:
                    continue
                if self._should_visit(normalized):
                    counter += 1
                    heapq.heappush(
                        queue,
                        (
                            self._priority(normalized, page.depth + 1),
                            counter,
                            DiscoveredPage(normalized, page.depth + 1),
                        ),
                    )

        ranked = sorted(visited, key=lambda page: self._content_score(page.url), reverse=True)
        selected: list[DiscoveredPage] = []
        selected_urls: set[str] = set()
        for page in ranked:
            if page.url in selected_urls:
                continue
            selected.append(page)
            selected_urls.add(page.url)
        logger.info("Crawler finalizado. Visitadas=%s seleccionadas=%s", len(visited), len(selected))
        return selected

    def _fetch_html(self, url: str) -> str | None:
        try:
            response = self.session.get(url, timeout=self.config.timeout_seconds)
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            logger.warning("No se pudo visitar %s: %s", url, exc)
            return None

    def _should_visit(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.netloc != self.config.domain:
            return False

        path = parsed.path or "/"
        if any(token in url.lower() for token in ("?query=", "?search=", "/search")):
            return False
        if self.config.include_prefixes and not any(
            path.startswith(prefix) for prefix in self.config.include_prefixes
        ):
            return False

        if any(path.startswith(prefix) for prefix in self.config.exclude_paths):
            return False

        blocked_suffixes = (".png", ".jpg", ".jpeg", ".svg", ".pdf", ".zip")
        return not path.endswith(blocked_suffixes)

    def _priority(self, url: str, depth: int) -> int:
        # lower numbers are visited first
        return -self._content_score(url) - depth

    def _content_score(self, url: str) -> int:
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        score = 0
        score += len(parts) * 10

        leaf = parts[-1].lower() if parts else "index"
        if leaf in {
            "docs",
            "documentation",
            "tutorials",
            "learn",
            "hardware",
            "software",
            "libraries",
            "language-reference",
            "programming",
            "api",
            "guides",
        }:
            score -= 30

        for token in ("tutorial", "guide", "reference", "example", "getting-started", "overview"):
            if token in url.lower():
                score += 8
        for token in ("asmx", "wsdl", "soap", "endpoint"):
            if token in url.lower():
                score += 12
        for token in ("retired", "legacy", "archive", "search", "tag", "category"):
            if token in url.lower():
                score -= 20
        return score

    def _discover_sitemap_urls(self) -> list[str]:
        candidates = [
            f"{self.config.origin}/robots.txt",
            f"{self.config.origin}/sitemap.xml",
            f"{self.config.origin}/sitemap_index.xml",
            f"{self.config.origin}/sitemap-index.xml",
        ]
        candidates.extend(self.config.sitemap_urls)

        found: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            normalized = canonicalize_url(candidate)
            if normalized in seen:
                continue
            seen.add(normalized)
            if normalized.endswith("/robots.txt"):
                extracted = self._extract_sitemaps_from_robots(normalized)
                if extracted:
                    logger.info("robots.txt reporto %s sitemaps", len(extracted))
                found.extend(extracted)
            elif self._head_ok(normalized):
                found.append(normalized)
        return list(dict.fromkeys(found))

    def _extract_sitemaps_from_robots(self, robots_url: str) -> list[str]:
        try:
            response = self.session.get(robots_url, timeout=self.config.timeout_seconds)
            if response.status_code >= 400:
                logger.debug("robots.txt no disponible en %s", robots_url)
                return []
        except requests.RequestException as exc:
            logger.debug("No se pudo leer robots.txt %s: %s", robots_url, exc)
            return []

        sitemaps: list[str] = []
        for line in response.text.splitlines():
            if line.lower().startswith("sitemap:"):
                _, sitemap_url = line.split(":", 1)
                sitemaps.append(canonicalize_url(sitemap_url.strip()))
        return sitemaps

    def _read_sitemap(self, sitemap_url: str) -> list[str]:
        try:
            response = self.session.get(sitemap_url, timeout=self.config.timeout_seconds)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("No se pudo leer sitemap %s: %s", sitemap_url, exc)
            return []

        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as exc:
            logger.warning("Sitemap invalido %s: %s", sitemap_url, exc)
            return []

        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls: list[str] = []
        if root.tag.endswith("sitemapindex"):
            for loc in root.findall(".//sm:sitemap/sm:loc", namespace):
                if loc.text:
                    urls.extend(self._read_sitemap(loc.text.strip()))
            return urls

        for loc in root.findall(".//sm:url/sm:loc", namespace):
            if loc.text:
                urls.append(canonicalize_url(loc.text.strip()))
        return urls

    def _head_ok(self, url: str) -> bool:
        try:
            response = self.session.head(
                url,
                timeout=self.config.timeout_seconds,
                allow_redirects=True,
            )
            return response.status_code < 400
        except requests.RequestException as exc:
            logger.debug("HEAD fallo para %s: %s", url, exc)
            return False

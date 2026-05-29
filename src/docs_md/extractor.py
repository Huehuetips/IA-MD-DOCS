from __future__ import annotations

import logging
import warnings

from bs4 import BeautifulSoup, Tag, XMLParsedAsHTMLWarning

from .utils import looks_like_xml


MAIN_SELECTORS = [
    "main",
    "article",
    ".markdown-body",
    ".theme-doc-markdown",
    ".content",
    ".prose",
    "[role='main']",
]

NOISE_SELECTORS = [
    "nav",
    "aside",
    "footer",
    "script",
    "style",
    ".breadcrumbs",
    ".pagination-nav",
    ".toc",
    ".table-of-contents",
    ".theme-doc-toc-desktop",
]


logger = logging.getLogger(__name__)


class MainContentExtractor:
    def extract(self, html: str) -> tuple[str, str, list[str]]:
        if looks_like_xml("", html):
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
                soup = BeautifulSoup(html, "html.parser")
        else:
            soup = BeautifulSoup(html, "html.parser")
        self._remove_global_noise(soup)
        main = self._select_main_node(soup)
        title = self._extract_title(main if isinstance(main, Tag) else soup, soup)

        for selector in NOISE_SELECTORS:
            for node in main.select(selector):
                node.decompose()

        headings = [
            node.get_text(" ", strip=True)
            for node in main.select("h1, h2, h3")
            if node.get_text(" ", strip=True)
        ]
        logger.debug(
            "Contenido extraido title=%s headings=%s html_bytes=%s",
            title,
            len(headings),
            len(str(main)),
        )
        return title, str(main), headings

    def _extract_title(self, node: Tag | BeautifulSoup, fallback_soup: BeautifulSoup) -> str:
        h1 = node.select_one("h1")
        if h1:
            return h1.get_text(" ", strip=True)
        if fallback_soup.title and fallback_soup.title.string:
            return fallback_soup.title.string.strip()
        return "Untitled"

    def _select_main_node(self, soup: BeautifulSoup) -> Tag:
        candidates: list[Tag] = []
        for selector in MAIN_SELECTORS:
            candidates.extend(soup.select(selector))

        for node in soup.select("article, main, section, div"):
            if self._is_candidate(node):
                candidates.append(node)

        best = None
        best_score = float("-inf")
        seen: set[int] = set()
        for candidate in candidates:
            marker = id(candidate)
            if marker in seen:
                continue
            seen.add(marker)
            score = self._score_candidate(candidate)
            if score > best_score:
                best = candidate
                best_score = score

        if best:
            return best
        if soup.body:
            return soup.body
        return soup

    def _remove_global_noise(self, soup: BeautifulSoup) -> None:
        for selector in NOISE_SELECTORS:
            for node in soup.select(selector):
                node.decompose()

    def _is_candidate(self, node: Tag) -> bool:
        if node.name not in {"article", "main", "section", "div"}:
            return False
        text = node.get_text(" ", strip=True)
        if len(text) < 300:
            return False
        if not node.select("h1, h2, h3, p, pre, code, table, ul, ol"):
            return False
        return True

    def _score_candidate(self, node: Tag) -> int:
        text = node.get_text(" ", strip=True)
        paragraphs = len(node.select("p"))
        headings = len(node.select("h1, h2, h3"))
        code_blocks = len(node.select("pre, code"))
        tables = len(node.select("table"))
        lists = len(node.select("ul, ol"))
        links = len(node.select("a"))
        list_items = len(node.select("li"))

        score = 0
        score += min(len(text) // 80, 120)
        score += paragraphs * 14
        score += headings * 18
        score += code_blocks * 24
        score += tables * 20
        score += lists * 6
        score -= links * 2
        score -= max(list_items - paragraphs * 2, 0)
        return score

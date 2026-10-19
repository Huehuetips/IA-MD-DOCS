from __future__ import annotations

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docs_md.crawler import DocumentationCrawler
from docs_md.models import PipelineConfig


class CrawlerTests(unittest.TestCase):
    def test_discover_sitemap_urls_uses_root_origin_including_port(self) -> None:
        config = PipelineConfig(
            root_url="http://example.com:1880/docs/index.html",
            output_dir=Path("/tmp/out"),
        )
        crawler = DocumentationCrawler(config)

        seen_urls: list[str] = []

        def fake_head(url: str) -> bool:
            seen_urls.append(url)
            return False

        with patch.object(crawler, "_extract_sitemaps_from_robots", return_value=[]):
            with patch.object(crawler, "_head_ok", side_effect=fake_head):
                crawler._discover_sitemap_urls()

        self.assertTrue(seen_urls)
        self.assertTrue(all(url.startswith("http://example.com:1880/") for url in seen_urls))
        self.assertFalse(any(url.startswith("https://") for url in seen_urls))

    def test_should_visit_allows_functional_query_urls(self) -> None:
        config = PipelineConfig(
            root_url="http://example.com:1880/docs/index.html",
            output_dir=Path("/tmp/out"),
        )
        crawler = DocumentationCrawler(config)
        self.assertTrue(
            crawler._should_visit("http://example.com:1880/wsCAEXLogisticsSB/wsCAEXLogisticsSB.asmx?op=AnularGuia")
        )

    def test_relative_links_resolve_against_real_document_url_with_trailing_slash(self) -> None:
        # Regresión: la URL canonicalizada no tiene barra final; usarla como base de
        # urljoin hacía subir un nivel los enlaces relativos (/en/stable/ -> /en/).
        config = PipelineConfig(
            root_url="https://docs.example.com/en/stable/",
            output_dir=Path("/tmp/out"),
        )
        crawler = DocumentationCrawler(config)
        index_html = '<a href="topics/authentication/">auth</a>'

        def fake_get(url: str, timeout: float) -> Mock:
            # La raíz se pide sin barra (PipelineConfig la canonicaliza) y el servidor
            # redirige a la versión con barra, como hace un sitio de docs real.
            is_root = url == config.root_url
            response = Mock()
            response.url = config.root_url + "/" if is_root else url
            response.text = index_html if is_root else "<p>sin enlaces</p>"
            response.raise_for_status = Mock()
            return response

        crawler.session = Mock(get=Mock(side_effect=fake_get))
        with patch.object(crawler, "_discover_sitemap_urls", return_value=[]):
            discovered = {page.url for page in crawler.discover()}

        self.assertIn("https://docs.example.com/en/stable/topics/authentication", discovered)
        self.assertNotIn("https://docs.example.com/en/topics/authentication", discovered)


if __name__ == "__main__":
    unittest.main()

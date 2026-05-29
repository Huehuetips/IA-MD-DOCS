from __future__ import annotations

import unittest
import sys
from pathlib import Path
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()

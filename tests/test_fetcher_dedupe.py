from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docs_md.fetcher import PlaywrightFetcher
from docs_md.models import ExtractedDocument, PipelineConfig
from docs_md.pipeline import DocumentationPipeline


def _doc(url: str, content_hash: str) -> ExtractedDocument:
    return ExtractedDocument(
        url=url,
        title=url,
        markdown="x",
        section="docs",
        doc_type="guide",
        headings=[],
        summary="",
        source_path=url,
        content_hash=content_hash,
    )


class PlaywrightFetcherTests(unittest.TestCase):
    def test_missing_browser_stops_runtime_and_is_not_retried_per_url(self) -> None:
        config = PipelineConfig(root_url="https://docs.example.com/", output_dir=Path("/tmp/out"))
        fetcher = PlaywrightFetcher(config)

        runtime = MagicMock()
        runtime.chromium.launch.side_effect = Exception("Executable doesn't exist\nrun playwright install")
        with patch("docs_md.fetcher.sync_playwright") as factory:
            factory.return_value.start.return_value = runtime

            with self.assertRaises(RuntimeError) as first:
                fetcher.fetch("https://docs.example.com/a")
            with self.assertRaises(RuntimeError) as second:
                fetcher.fetch("https://docs.example.com/b")

        self.assertIn("playwright install chromium", str(first.exception))
        self.assertEqual(str(first.exception), str(second.exception))
        runtime.stop.assert_called_once()
        factory.return_value.start.assert_called_once()


class UniqueByContentTests(unittest.TestCase):
    def test_keeps_highest_scored_copy_of_duplicated_content(self) -> None:
        stable = _doc("https://docs.example.com/en/stable/intro", "h1")
        latest = _doc("https://docs.example.com/en/latest/intro", "h1")
        other = _doc("https://docs.example.com/en/stable/other", "h2")
        ranked = [(9, stable), (8, latest), (7, other)]

        result = DocumentationPipeline._unique_by_content(ranked)

        self.assertEqual([doc.url for _, doc in result], [stable.url, other.url])

    def test_documents_without_hash_are_never_collapsed(self) -> None:
        a = _doc("https://docs.example.com/a", "")
        b = _doc("https://docs.example.com/b", "")
        result = DocumentationPipeline._unique_by_content([(2, a), (1, b)])
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docs_md.models import PipelineConfig
from docs_md.utils import (
    canonicalize_url,
    looks_like_xml,
    output_path_for_url,
    site_origin,
    source_path_for_url,
)


class UtilsTests(unittest.TestCase):
    def test_canonicalize_url_preserves_functional_query_and_sorts(self) -> None:
        url = canonicalize_url("http://example.com/foo/bar/?b=2&a=1#frag")
        self.assertEqual(url, "http://example.com/foo/bar?a=1&b=2")

    def test_canonicalize_url_strips_tracking_params(self) -> None:
        url = canonicalize_url(
            "http://example.com/docs/page?utm_source=newsletter&op=AnularGuia"
        )
        self.assertEqual(url, "http://example.com/docs/page?op=AnularGuia")

    def test_site_origin_preserves_port(self) -> None:
        self.assertEqual(site_origin("http://example.com:1880/docs/page?op=1"), "http://example.com:1880")

    def test_output_path_for_url_includes_query_identity(self) -> None:
        path = output_path_for_url(
            Path("/tmp/out"),
            "http://example.com/wsCAEXLogisticsSB/wsCAEXLogisticsSB.asmx?op=AnularGuia",
        )
        self.assertEqual(
            path.as_posix(),
            "/tmp/out/wscaexlogisticssb/wscaexlogisticssb-asmx/op-anularguia.md",
        )

    def test_source_path_for_url_includes_query_identity(self) -> None:
        self.assertEqual(
            source_path_for_url("http://example.com/wsCAEXLogisticsSB/wsCAEXLogisticsSB.asmx?WSDL"),
            "wscaexlogisticssb/wscaexlogisticssb-asmx/wsdl",
        )

    def test_output_path_for_url_handles_bare_query_token(self) -> None:
        path = output_path_for_url(
            Path("/tmp/out"),
            "http://example.com/wsCAEXLogisticsSB/wsCAEXLogisticsSB.asmx?WSDL",
        )
        self.assertEqual(
            path.as_posix(),
            "/tmp/out/wscaexlogisticssb/wscaexlogisticssb-asmx/wsdl.md",
        )

    def test_pipeline_config_domain_and_origin(self) -> None:
        config = PipelineConfig(
            root_url="http://example.com:1880/docs/page?op=1",
            output_dir=Path("/tmp/out"),
        )
        self.assertEqual(config.domain, "example.com:1880")
        self.assertEqual(config.origin, "http://example.com:1880")

    def test_looks_like_xml_detects_wsdl_urls(self) -> None:
        self.assertTrue(looks_like_xml("http://example.com/service.asmx?WSDL", "<definitions />"))


if __name__ == "__main__":
    unittest.main()

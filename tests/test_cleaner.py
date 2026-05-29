from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docs_md.cleaner import infer_doc_type, is_low_value_document


class CleanerTests(unittest.TestCase):
    def test_infer_doc_type_recognizes_asmx_reference_pages(self) -> None:
        doc_type = infer_doc_type(
            "http://example.com/wsCAEXLogisticsSB/wsCAEXLogisticsSB.asmx?op=AnularGuia",
            [],
        )
        self.assertEqual(doc_type, "reference")

    def test_low_value_filter_relaxes_for_reference_pages(self) -> None:
        markdown = "# Service\n\n- [One](x)\n- [Two](x)\n"
        self.assertFalse(
            is_low_value_document(
                markdown,
                headings=["Service"],
                url="http://example.com/service.asmx?op=One",
                doc_type="reference",
            )
        )

    def test_low_value_filter_keeps_empty_pages_rejected(self) -> None:
        self.assertTrue(
            is_low_value_document(
                "",
                headings=[],
                url="http://example.com/service.asmx?op=One",
                doc_type="reference",
            )
        )


if __name__ == "__main__":
    unittest.main()

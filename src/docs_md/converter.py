from __future__ import annotations

import logging

from markdownify import markdownify as to_markdown

from .utils import collapse_blank_lines


logger = logging.getLogger(__name__)


class MarkdownConverter:
    def convert(self, html: str) -> str:
        markdown = to_markdown(
            html,
            heading_style="ATX",
            bullets="-",
            strip=["img"],
        )
        collapsed = collapse_blank_lines(markdown)
        logger.debug(
            "Conversion HTML->Markdown completada input_bytes=%s output_bytes=%s",
            len(html),
            len(collapsed),
        )
        return collapsed

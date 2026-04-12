from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

import yaml

from .models import ExtractedDocument
from .utils import output_path_for_url


logger = logging.getLogger(__name__)


class DocumentWriter:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.meta_dir = output_dir / "_meta"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.meta_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Writer inicializado output_dir=%s meta_dir=%s", self.output_dir, self.meta_dir)

    def write_document(self, document: ExtractedDocument) -> Path:
        destination = output_path_for_url(self.output_dir, document.url)
        destination.parent.mkdir(parents=True, exist_ok=True)

        frontmatter = {
            "title": document.title,
            "source": document.url,
            "section": document.section,
            "last_scraped": document.scraped_at,
            "type": document.doc_type,
        }
        body = f"---\n{yaml.safe_dump(frontmatter, sort_keys=False)}---\n\n{document.markdown}"
        destination.write_text(body, encoding="utf-8")
        logger.debug("Documento serializado en %s", destination)
        return destination

    def write_index(self, documents: list[ExtractedDocument]) -> Path:
        index_path = self.meta_dir / "index.json"
        payload = [asdict(document) for document in documents]
        index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.debug("Index serializado en %s documentos=%s", index_path, len(documents))
        return index_path

    def output_path_for(self, url: str) -> Path:
        return output_path_for_url(self.output_dir, url)

    def read_document_markdown(self, url: str) -> str:
        path = self.output_path_for(url)
        if not path.exists():
            return ""
        content = path.read_text(encoding="utf-8")
        if content.startswith("---\n"):
            parts = content.split("---\n", 2)
            if len(parts) == 3:
                return parts[2].lstrip()
        return content

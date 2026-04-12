from __future__ import annotations

import logging
from pathlib import Path

from .cache import CacheStore
from .cleaner import (
    DeterministicCleaner,
    OptionalAICleaner,
    document_value_score,
    infer_doc_type,
    infer_section,
    is_low_value_document,
    summarize,
)
from .converter import MarkdownConverter
from .crawler import DocumentationCrawler
from .extractor import MainContentExtractor
from .fetcher import RequestsFetcher
from .fetcher import PlaywrightFetcher
from .models import ExtractedDocument, PipelineConfig
from .utils import path_from_url, stable_hash
from .writer import DocumentWriter


logger = logging.getLogger(__name__)


class DocumentationPipeline:
    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.crawler = DocumentationCrawler(config)
        self.fetcher = RequestsFetcher(config)
        self.playwright_fetcher = PlaywrightFetcher(config)
        self.extractor = MainContentExtractor()
        self.converter = MarkdownConverter()
        self.cleaner = DeterministicCleaner()
        self.ai_cleaner = OptionalAICleaner(
            mode=config.ai_mode,
            command=config.ai_command,
            model=config.ai_model,
            timeout_seconds=config.ai_timeout_seconds,
        )
        self.writer = DocumentWriter(config.output_dir)
        self.cache = CacheStore(self.writer.meta_dir)

    def run(self) -> tuple[list[ExtractedDocument], Path]:
        logger.info("Iniciando descubrimiento de URLs desde %s", self.config.root_url)
        discovered = self.crawler.discover()
        logger.info("Descubrimiento completado. URLs candidatas=%s", len(discovered))
        candidate_budget = min(len(discovered), max(self.config.max_pages * 3, 20))
        logger.info(
            "Se evaluaran %s URLs candidatas para seleccionar hasta %s documentos finales",
            candidate_budget,
            self.config.max_pages,
        )
        candidates: list[tuple[int, ExtractedDocument]] = []
        try:
            for index, page in enumerate(discovered[:candidate_budget], start=1):
                logger.info(
                    "Procesando candidata %s/%s depth=%s url=%s",
                    index,
                    candidate_budget,
                    page.depth,
                    page.url,
                )
                try:
                    html = self.fetcher.fetch(page.url)
                except Exception as exc:
                    logger.warning("No se pudo descargar %s: %s", page.url, exc)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("Detalle del fallo de requests", exc_info=True)
                    continue

                title, main_html, headings = self.extractor.extract(html)
                if self._should_retry_with_playwright(main_html, headings):
                    logger.info("Contenido insuficiente. Reintentando con Playwright: %s", page.url)
                    try:
                        html = self.playwright_fetcher.fetch(page.url)
                        title, main_html, headings = self.extractor.extract(html)
                    except Exception as exc:
                        logger.warning("Falló el fallback con Playwright para %s: %s", page.url, exc)
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug("Detalle del fallo de Playwright", exc_info=True)
                source_hash = stable_hash(main_html)
                output_path = self.writer.output_path_for(page.url)
                cached = self.cache.get(page.url)
                if (
                    self.config.cache_enabled
                    and cached
                    and cached.get("source_hash") == source_hash
                    and output_path.exists()
                ):
                    document = ExtractedDocument(
                        url=page.url,
                        title=cached.get("title", title),
                        markdown=self.writer.read_document_markdown(page.url),
                        section=cached.get("section", infer_section(page.url)),
                        doc_type=cached.get("doc_type", infer_doc_type(page.url, headings)),
                        headings=cached.get("headings", headings),
                        summary=cached.get("summary", ""),
                        source_path=path_from_url(page.url),
                        content_hash=cached.get("content_hash", ""),
                        source_hash=source_hash,
                    )
                    candidates.append((cached.get("score", 0), document))
                    logger.info("Cache hit. Reutilizando %s -> %s", page.url, output_path)
                    continue
                markdown = self.converter.convert(main_html)
                markdown = self.cleaner.clean(markdown)
                markdown = self.ai_cleaner.clean(markdown, title, page.url)
                if is_low_value_document(markdown, headings):
                    logger.info("Documento descartado por bajo valor: %s", page.url)
                    continue
                content_hash = stable_hash(markdown)

                document = ExtractedDocument(
                    url=page.url,
                    title=title,
                    markdown=markdown,
                    section=infer_section(page.url),
                    doc_type=infer_doc_type(page.url, headings),
                    headings=headings,
                    summary=summarize(title, markdown),
                    source_path=path_from_url(page.url),
                    content_hash=content_hash,
                    source_hash=source_hash,
                )
                score = document_value_score(markdown, headings, page.url)
                self.cache.update(
                    page.url,
                    {
                        "title": document.title,
                        "section": document.section,
                        "doc_type": document.doc_type,
                        "headings": document.headings,
                        "summary": document.summary,
                        "content_hash": content_hash,
                        "source_hash": source_hash,
                        "score": score,
                        "output_path": str(output_path),
                    },
                )
                candidates.append((score, document))
                logger.info(
                    "Documento aceptado title=%s score=%s output=%s",
                    document.title,
                    score,
                    output_path,
                )
        finally:
            self.playwright_fetcher.close()
            logger.debug("Recursos de Playwright cerrados.")

        documents: list[ExtractedDocument] = []
        ranked_candidates = sorted(candidates, key=lambda item: item[0], reverse=True)
        logger.info("Escribiendo documentos finales. Candidatos rankeados=%s", len(ranked_candidates))
        for rank, (score, document) in enumerate(ranked_candidates, start=1):
            if document.markdown:
                destination = self.writer.write_document(document)
                logger.info(
                    "Escrito documento %s/%s rank=%s score=%s path=%s",
                    len(documents) + 1,
                    min(len(ranked_candidates), self.config.max_pages),
                    rank,
                    score,
                    destination,
                )
            documents.append(document)
            if len(documents) >= self.config.max_pages:
                break

        index_path = self.writer.write_index(documents)
        logger.info("Indice generado en %s", index_path)
        cache_path = self.cache.save()
        logger.info("Cache manifest guardado en %s", cache_path)
        return documents, index_path

    def _should_retry_with_playwright(self, main_html: str, headings: list[str]) -> bool:
        if self.config.render_mode == "requests":
            return False
        if self.config.render_mode == "playwright":
            return True

        stripped = main_html.strip().lower()
        if len(stripped) < 200:
            return True
        if headings:
            return False
        return True

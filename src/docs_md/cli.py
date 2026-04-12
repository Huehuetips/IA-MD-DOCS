from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .logging_utils import configure_logging
from .models import PipelineConfig
from .pipeline import DocumentationPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docs-md",
        description="Crawl a documentation site and export Markdown files.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    crawl = subparsers.add_parser("crawl", help="Run the documentation pipeline.")
    crawl.add_argument("url", help="Root URL of the documentation site.")
    crawl.add_argument("--output", required=True, help="Output directory.")
    crawl.add_argument(
        "--include-prefix",
        action="append",
        default=[],
        help="Restrict crawling to matching path prefixes, e.g. /docs.",
    )
    crawl.add_argument(
        "--exclude-path",
        action="append",
        default=[],
        help="Exclude path prefixes, e.g. /blog.",
    )
    crawl.add_argument(
        "--sitemap-url",
        action="append",
        default=[],
        help="Additional sitemap URLs to seed discovery.",
    )
    crawl.add_argument("--max-pages", type=int, default=100)
    crawl.add_argument(
        "--max-visits",
        type=int,
        default=None,
        help="Maximum pages to visit while discovering leaf content.",
    )
    crawl.add_argument("--timeout", type=int, default=15)
    crawl.add_argument(
        "--ai-mode",
        choices=["off", "rewrite"],
        default="off",
        help="Optional AI post-processing mode.",
    )
    crawl.add_argument(
        "--ai-command",
        default="copilot",
        help="Shell command template for AI cleanup. Placeholders: {model}, {title}, {url}. Prompt is sent via stdin.",
    )
    crawl.add_argument(
        "--ai-model",
        default="claude-sonnet-4.5",
        help="Model name passed to the AI command template.",
    )
    crawl.add_argument(
        "--ai-timeout",
        type=int,
        default=120,
        help="Timeout for the AI cleanup command in seconds.",
    )
    crawl.add_argument(
        "--render-mode",
        choices=["auto", "requests", "playwright"],
        default="auto",
        help="HTML acquisition mode. Auto retries with Playwright on thin pages.",
    )
    crawl.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable manifest-based reuse of unchanged pages.",
    )
    crawl.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Nivel de detalle de logs mostrado durante la ejecucion.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(getattr(args, "log_level", "INFO"))
    logger = logging.getLogger(__name__)

    if args.command == "crawl":
        config = PipelineConfig(
            root_url=args.url,
            output_dir=Path(args.output),
            include_prefixes=args.include_prefix,
            exclude_paths=args.exclude_path,
            sitemap_urls=args.sitemap_url,
            max_pages=args.max_pages,
            max_visits=args.max_visits or max(args.max_pages * 10, 200),
            timeout_seconds=args.timeout,
            ai_mode=args.ai_mode,
            ai_command=args.ai_command,
            ai_model=args.ai_model,
            ai_timeout_seconds=args.ai_timeout,
            render_mode=args.render_mode,
            cache_enabled=not args.no_cache,
        )
        logger.info(
            "Inicio de crawl root=%s output=%s max_pages=%s max_visits=%s render_mode=%s ai_mode=%s cache=%s",
            config.root_url,
            config.output_dir,
            config.max_pages,
            config.max_visits,
            config.render_mode,
            config.ai_mode,
            config.cache_enabled,
        )
        try:
            pipeline = DocumentationPipeline(config)
            documents, index_path = pipeline.run()
        except Exception:
            logger.exception("La ejecucion del pipeline termino con error.")
            raise

        logger.info("Procesadas %s paginas.", len(documents))
        logger.info("Indice escrito en %s", index_path)


if __name__ == "__main__":
    main()

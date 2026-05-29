from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from .utils import canonicalize_url, site_origin


@dataclass(slots=True)
class PipelineConfig:
    root_url: str
    output_dir: Path
    include_prefixes: list[str] = field(default_factory=list)
    exclude_paths: list[str] = field(default_factory=list)
    sitemap_urls: list[str] = field(default_factory=list)
    max_pages: int = 100
    max_visits: int = 1000
    timeout_seconds: int = 15
    ai_mode: str = "off"
    render_mode: str = "auto"
    cache_enabled: bool = True
    ai_model: str = "claude-sonnet-4.5"
    ai_command: str = "copilot"
    ai_timeout_seconds: int = 120
    user_agent: str = "docs-md-pipeline/0.1"

    def __post_init__(self) -> None:
        self.root_url = canonicalize_url(self.root_url)
        if self.max_visits < self.max_pages:
            self.max_visits = self.max_pages

    @property
    def domain(self) -> str:
        return urlparse(self.root_url).netloc

    @property
    def origin(self) -> str:
        return site_origin(self.root_url)


@dataclass(slots=True)
class DiscoveredPage:
    url: str
    depth: int


@dataclass(slots=True)
class ExtractedDocument:
    url: str
    title: str
    markdown: str
    section: str
    doc_type: str
    headings: list[str]
    summary: str
    source_path: str
    content_hash: str = ""
    source_hash: str = ""
    scraped_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).date().isoformat()
    )

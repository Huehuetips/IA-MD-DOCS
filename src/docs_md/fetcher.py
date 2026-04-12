from __future__ import annotations

import logging

import requests
from playwright.sync_api import Browser, Playwright, sync_playwright

from .models import PipelineConfig


logger = logging.getLogger(__name__)


class RequestsFetcher:
    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = config.user_agent

    def fetch(self, url: str) -> str:
        logger.debug("HTTP GET via requests: %s", url)
        response = self.session.get(url, timeout=self.config.timeout_seconds)
        response.raise_for_status()
        logger.debug(
            "HTTP OK via requests status=%s bytes=%s url=%s",
            response.status_code,
            len(response.text),
            url,
        )
        return response.text


class PlaywrightFetcher:
    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    def fetch(self, url: str) -> str:
        browser = self._get_browser()
        logger.debug("HTTP GET via Playwright: %s", url)
        page = browser.new_page(user_agent=self.config.user_agent)
        page.goto(url, wait_until="domcontentloaded", timeout=self.config.timeout_seconds * 1000)
        page.wait_for_timeout(1500)
        html = page.content()
        page.close()
        logger.debug("HTML obtenido via Playwright bytes=%s url=%s", len(html), url)
        return html

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
            self._browser = None
            logger.debug("Browser de Playwright cerrado.")
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None
            logger.debug("Runtime de Playwright detenido.")

    def _get_browser(self) -> Browser:
        if self._browser is None:
            logger.info("Inicializando navegador headless de Playwright.")
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
        return self._browser

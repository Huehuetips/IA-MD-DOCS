from __future__ import annotations

import json
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


class CacheStore:
    def __init__(self, meta_dir: Path) -> None:
        self.meta_dir = meta_dir
        self.meta_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.meta_dir / "cache_manifest.json"
        self._data = self._load()
        logger.debug("Cache cargada desde %s registros=%s", self.manifest_path, len(self._data))

    def get(self, url: str) -> dict | None:
        return self._data.get(url)

    def update(self, url: str, record: dict) -> None:
        self._data[url] = record
        logger.debug("Cache actualizada para %s", url)

    def save(self) -> Path:
        self.manifest_path.write_text(
            json.dumps(self._data, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        logger.debug("Cache guardada en %s registros=%s", self.manifest_path, len(self._data))
        return self.manifest_path

    def _load(self) -> dict[str, dict]:
        if not self.manifest_path.exists():
            return {}
        try:
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Cache manifest invalido en %s. Se reconstruira.", self.manifest_path)
            return {}

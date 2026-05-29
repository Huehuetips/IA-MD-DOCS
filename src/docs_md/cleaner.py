from __future__ import annotations

import logging
import re
import shlex
import subprocess

from .utils import collapse_blank_lines, path_from_url


logger = logging.getLogger(__name__)


class DeterministicCleaner:
    def clean(self, markdown: str) -> str:
        original_length = len(markdown)
        cleaned = markdown
        cleaned = self._fix_common_mojibake(cleaned)
        cleaned = re.sub(r"(?im)^on this page\s*$", "", cleaned)
        cleaned = re.sub(r"(?im)^edit this page\s*$", "", cleaned)
        cleaned = re.sub(r"(?im)^previous\s*$", "", cleaned)
        cleaned = re.sub(r"(?im)^next\s*$", "", cleaned)
        cleaned = re.sub(r"(?im)^all docs\s*$", "", cleaned)
        cleaned = re.sub(r"(?im)^all docs?\s*$", "", cleaned)
        cleaned = re.sub(r"(?im)^go back\s*$", "", cleaned)
        cleaned = re.sub(r"(?im)^type to search\s*$", "", cleaned)
        cleaned = re.sub(r"(?im)^get started\s*$", "", cleaned)
        cleaned = re.sub(r"(?im)^view all\s*$", "", cleaned)
        cleaned = re.sub(r"(?is)#### suggest changes.*$", "", cleaned)
        cleaned = re.sub(r"(?is)#### need support\?.*$", "", cleaned)
        cleaned = re.sub(r"(?is)#### license.*$", "", cleaned)
        cleaned = re.sub(r"(?is)#### was this article helpful\?.*$", "", cleaned)
        cleaned = re.sub(r"(?is)#### connect and contribute.*$", "", cleaned)
        cleaned = re.sub(r"(?is)#### community.*$", "", cleaned)
        cleaned = re.sub(r"(?is)product compliance.*$", "", cleaned)
        cleaned = self._drop_noise_lines(cleaned)
        collapsed = collapse_blank_lines(cleaned)
        logger.debug(
            "Limpieza deterministica completada input_bytes=%s output_bytes=%s",
            original_length,
            len(collapsed),
        )
        return collapsed

    def _drop_noise_lines(self, markdown: str) -> str:
        blocked = {
            "[all docs](/)",
            "[go back](/)",
            "all docs",
            "go back",
            "table of contents",
            "this page",
            "type to search",
            "get started",
            "sort bynewestdifficultyname",
            "sort bystarsnameforksrecents",
        }
        lines = []
        for line in markdown.splitlines():
            normalized = line.strip().lower()
            if normalized in blocked:
                continue
            lines.append(line)
        return "\n".join(lines)

    def _fix_common_mojibake(self, text: str) -> str:
        replacements = {
            "Donât": "Don't",
            "â": "'",
            "â": "-",
            "â¢": "™",
            "Â®": "®",
            "Â©": "©",
            "Â¶": "",
            "â": "—",
            "â": '"',
            "â": '"',
            "Wi-FiÂ®": "Wi-Fi®",
            "LoRaÂ®": "LoRa®",
            "ArduinoÂ®": "Arduino®",
        }
        for bad, good in replacements.items():
            text = text.replace(bad, good)
        return text


class OptionalAICleaner:
    def __init__(
        self,
        mode: str = "off",
        command: str = "",
        model: str = "claude-sonnet-4.5",
        timeout_seconds: int = 120,
    ) -> None:
        self.mode = mode
        self.command = command
        self.model = model
        self.timeout_seconds = timeout_seconds

    def clean(self, markdown: str, title: str, url: str) -> str:
        if self.mode == "off":
            logger.debug("Limpieza AI desactivada para %s", url)
            return markdown
        if not self.command.strip():
            logger.warning("Limpieza AI omitida porque no hay comando configurado para %s", url)
            return markdown

        command = self.command.format(
            model=self.model,
            title=title.replace('"', "'"),
            url=url,
        )
        prompt = self._build_prompt(markdown, title, url)
        logger.info("Ejecutando limpieza AI para %s con modelo=%s", url, self.model)
        try:
            if self._is_copilot_command(command):
                result = subprocess.run(
                    self._build_copilot_args(command, prompt),
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    shell=False,
                    check=False,
                )
            else:
                result = subprocess.run(
                    command,
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    shell=True,
                    check=False,
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("Limpieza AI fallo para %s: %s", url, exc)
            return markdown

        if result.returncode != 0:
            stderr = result.stderr.strip() if result.stderr else "sin detalle"
            logger.warning(
                "Limpieza AI devolvio codigo=%s para %s. stderr=%s",
                result.returncode,
                url,
                stderr,
            )
            return markdown

        cleaned = result.stdout.strip()
        if not cleaned:
            logger.warning("Limpieza AI devolvio salida vacia para %s", url)
            return markdown
        collapsed = collapse_blank_lines(cleaned)
        logger.info("Limpieza AI aplicada correctamente a %s", url)
        return collapsed

    def _build_prompt(self, markdown: str, title: str, url: str) -> str:
        return f"""You are cleaning Markdown extracted from a documentation website.

Rules:
- Output Markdown only.
- Preserve technical accuracy.
- Preserve code blocks unless clearly malformed.
- Remove navigation, support prompts, edit links, feedback prompts, and repeated boilerplate.
- Keep useful headings, paragraphs, lists, tables, and links.
- Do not invent content.

Title: {title}
URL: {url}

Markdown:

{markdown}
"""

    def _is_copilot_command(self, command: str) -> bool:
        stripped = command.strip().lower()
        return stripped == "copilot" or stripped.startswith("copilot ")

    def _build_copilot_args(self, command: str, prompt: str) -> list[str]:
        args = shlex.split(command, posix=False)
        if "--model" not in args:
            args.extend(["--model", self.model])
        if "-p" not in args and "--prompt" not in args:
            args.extend(["-p", prompt])
        if "-s" not in args and "--silent" not in args:
            args.append("-s")
        if "--allow-all-tools" not in args and "--allow-all" not in args and "--yolo" not in args:
            args.append("--allow-all-tools")
        return args


def infer_section(url: str) -> str:
    path = path_from_url(url)
    return path.split("/")[0]


def infer_doc_type(url: str, headings: list[str]) -> str:
    lowered = " ".join(headings).lower()
    url_lower = url.lower()
    if any(token in url_lower for token in ("/api/", ".wsdl", "?wsdl", ".asmx", "?op=", ".xml")):
        return "reference"
    if "endpoint" in lowered:
        return "reference"
    if "faq" in url_lower or "faq" in lowered:
        return "faq"
    return "guide"


def summarize(title: str, markdown: str) -> str:
    content = re.sub(r"(?m)^#.*$", "", markdown)
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    body = " ".join(lines[:3])[:180].strip()
    return body or f"Documentation page for {title}."


def is_low_value_document(markdown: str, headings: list[str], url: str = "", doc_type: str = "") -> bool:
    lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    if not lines:
        return True

    text_chars = sum(len(line) for line in lines)
    link_lines = sum(1 for line in lines if line.startswith("[") and "](" in line)
    heading_lines = sum(1 for line in lines if line.startswith("#"))
    paragraph_lines = sum(
        1
        for line in lines
        if not line.startswith(("#", "[", "-", "*", "`")) and len(line.split()) >= 8
    )

    url_lower = url.lower()
    service_page = any(token in url_lower for token in (".asmx", ".wsdl", "?wsdl", "?op=", ".xml"))
    reference_page = doc_type == "reference" or service_page
    if reference_page:
        return text_chars < 80 and heading_lines == 0 and link_lines == 0

    if text_chars < 250:
        return True
    if paragraph_lines == 0 and link_lines > 12:
        return True
    if heading_lines <= 1 and link_lines > 20:
        return True
    if len(headings) <= 1 and link_lines > 25:
        return True
    return False


def document_value_score(markdown: str, headings: list[str], url: str) -> int:
    lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    text_chars = sum(len(line) for line in lines)
    link_lines = sum(1 for line in lines if line.startswith("[") and "](" in line)
    paragraph_lines = sum(
        1
        for line in lines
        if not line.startswith(("#", "[", "-", "*", "`")) and len(line.split()) >= 8
    )
    code_fences = markdown.count("```")

    score = 0
    score += min(text_chars // 50, 80)
    score += paragraph_lines * 6
    score += len(headings) * 4
    score += code_fences * 10
    score -= link_lines * 2

    lowered = url.lower()
    for token in ("tutorial", "guide", "reference", "api", "getting-started", "example"):
        if token in lowered:
            score += 8
    for token in ("retired", "legacy", "archive"):
        if token in lowered:
            score -= 20
    return score

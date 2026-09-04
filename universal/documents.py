"""Pull readable text from a dropped document. Optional PDF libs; no extra required deps."""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

TEXT_CHARS = 40_000
MAX_READ_BYTES = 2_000_000
TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".json",
    ".csv",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".html",
    ".htm",
    ".xml",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".log",
    ".rst",
    ".css",
    ".env",
}


def clip_text(text: str, limit: int = TEXT_CHARS) -> str:
    cleaned = text.replace("\x00", "")
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit] + "\n\n[…truncated after about 5,000 words]"


def extract_text(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES or suffix == ".rtf":
        raw = path.read_bytes()[:MAX_READ_BYTES]
        return clip_text(raw.decode("utf-8", errors="replace"))
    if suffix == ".docx":
        return _docx_text(path)
    if suffix == ".pdf":
        return _pdf_text(path)
    if suffix in {".html", ".htm"}:
        return _html_text(path)
    raw = path.read_bytes()[:4096]
    if not raw or b"\x00" in raw[:512]:
        return None
    try:
        sample = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if sum(1 for ch in sample if ch.isprintable() or ch.isspace()) < len(sample) * 0.85:
        return None
    return clip_text(path.read_bytes()[:MAX_READ_BYTES].decode("utf-8", errors="replace"))


def _docx_text(path: Path) -> str | None:
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml")
    except (OSError, KeyError, zipfile.BadZipFile):
        return None
    root = ET.fromstring(xml)
    parts = [node.text for node in root.iter() if node.tag.endswith("}t") and node.text]
    text = "\n".join(parts).strip()
    return clip_text(text) if text else None


def _html_text(path: Path) -> str | None:
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw, "html.parser")
        return clip_text(soup.get_text("\n", strip=True))
    except Exception:
        return clip_text(raw)


def _pdf_text(path: Path) -> str | None:
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]

        reader = PdfReader(str(path))
        pages = [(page.extract_text() or "") for page in reader.pages]
        text = "\n".join(pages).strip()
        return clip_text(text) if text else None
    except Exception:
        pass
    try:
        from PyPDF2 import PdfReader as LegacyReader  # type: ignore[import-not-found]

        reader = LegacyReader(str(path))
        pages = [(page.extract_text() or "") for page in reader.pages]
        text = "\n".join(pages).strip()
        return clip_text(text) if text else None
    except Exception:
        return None

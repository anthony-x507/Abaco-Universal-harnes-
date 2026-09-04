from __future__ import annotations

import zipfile
from pathlib import Path

from universal.documents import extract_text


def test_extract_text_from_markdown(tmp_path: Path) -> None:
    path = tmp_path / "note.md"
    path.write_text("# Hello\n\nThis is a long enough note.", encoding="utf-8")
    text = extract_text(path)
    assert text is not None
    assert "Hello" in text
    assert "long enough" in text


def test_extract_text_from_docx(tmp_path: Path) -> None:
    path = tmp_path / "letter.docx"
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>Invoice steps</w:t></w:r></w:p></w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", xml)
    assert extract_text(path) == "Invoice steps"


def test_binary_without_text_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "blob.bin"
    path.write_bytes(b"\x00\x01\x02\x03\xff")
    assert extract_text(path) is None

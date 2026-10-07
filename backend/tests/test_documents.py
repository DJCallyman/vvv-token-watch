"""Tests for Phase 3 document parsing and embedding helpers."""

from __future__ import annotations

import base64
import io

import pytest
from fastapi import HTTPException

from backend.api.routes.documents import (
    DocumentParseRequest,
    _decode_request,
    extract_document_text,
)
from backend.core import embeddings


def test_extract_text_markdown_json():
    text, fmt = extract_document_text("notes.txt", b"hello world")
    assert (text, fmt) == ("hello world", "text")

    text, fmt = extract_document_text("readme.md", b"# Title")
    assert fmt == "markdown"
    assert text.startswith("# Title")

    text, fmt = extract_document_text("data.json", b'{"a": 1}')
    assert fmt == "json"
    assert '"a": 1' in text


def test_extract_pdf_round_trip():
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    with pytest.raises(ValueError) as exc:
        extract_document_text("blank.pdf", buffer.getvalue())
    assert "no extractable text" in str(exc.value)


def test_extract_rejects_binary_and_invalid_pdf():
    with pytest.raises(ValueError):
        extract_document_text("blob.bin", b"\xff\xfe\x00\x01")
    with pytest.raises(ValueError):
        extract_document_text("bad.pdf", b"not a pdf")


def test_decode_request_requires_content():
    with pytest.raises(HTTPException) as exc:
        _decode_request(DocumentParseRequest(filename="a.txt"))
    assert exc.value.status_code == 422

    with pytest.raises(HTTPException) as exc:
        _decode_request(
            DocumentParseRequest(filename="a.txt", content_base64="not base64!")
        )
    assert exc.value.status_code == 422

    content, kind = _decode_request(
        DocumentParseRequest(
            filename="a.txt", content_base64=base64.b64encode(b"hi").decode()
        )
    )
    assert content == b"hi"
    assert kind == "base64"

    content, kind = _decode_request(
        DocumentParseRequest(filename="a.txt", text="plain")
    )
    assert content == b"plain"
    assert kind == "text"


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------


def test_cosine_similarity_edge_cases():
    assert embeddings.cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)
    assert embeddings.cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)
    assert embeddings.cosine_similarity([0, 0], [1, 1]) == 0.0
    assert embeddings.cosine_similarity([1], [1, 2]) == 0.0


@pytest.mark.asyncio
async def test_rank_by_similarity_orders_documents(monkeypatch):
    async def fake_embed(client, model, texts):
        return [
            [1.0, 0.0],  # query
            [1.0, 0.0],  # doc 0 (best)
            [0.5, 0.5],  # doc 1
            [0.0, 1.0],  # doc 2 (worst)
        ]

    monkeypatch.setattr(embeddings, "embed_texts", fake_embed)
    ranked = await embeddings.rank_by_similarity(
        None, "model", "q", ["a", "b", "c"], top_k=2
    )
    assert [index for index, _ in ranked] == [0, 1]


@pytest.mark.asyncio
async def test_rank_by_similarity_empty_documents():
    assert await embeddings.rank_by_similarity(None, "model", "q", []) == []

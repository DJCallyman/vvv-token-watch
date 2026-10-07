"""Whitepaper, report, and document parsing workflows (Phase 3)."""

import base64
import binascii
import io
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.api.routes.ai_common import extract_chat_text, get_client
from backend.config import Settings, get_settings
from backend.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_DOCUMENT_CHARS = 200_000
MAX_CONTENT_BYTES = 4_000_000


class DocumentParseRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    text: Optional[str] = Field(None, max_length=MAX_DOCUMENT_CHARS * 2)
    content_base64: Optional[str] = Field(None, max_length=MAX_CONTENT_BYTES * 2)


class DocumentAskRequest(BaseModel):
    document_text: str = Field(..., min_length=1, max_length=MAX_DOCUMENT_CHARS)
    question: str = Field(..., min_length=3, max_length=500)


def extract_document_text(filename: str, content: bytes) -> Tuple[str, str]:
    """Extract text from supported formats. Returns ``(text, format)``.

    Supported: ``.pdf`` (pypdf), and UTF-8-decodable text/markdown/json.
    Raises ``ValueError`` with a clear message for anything else.
    """
    lower = filename.lower()
    if lower.endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover - dependency is pinned
            raise ValueError("PDF support is not installed") from exc
        try:
            reader = PdfReader(io.BytesIO(content))
            pages = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:
            raise ValueError(f"Could not read PDF: {type(exc).__name__}") from exc
        text = "\n\n".join(pages).strip()
        if not text:
            raise ValueError("PDF contained no extractable text")
        return text, "pdf"
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "Unsupported document encoding or format (expected PDF, Markdown, text, or JSON)"
        ) from exc
    if lower.endswith(".json"):
        try:
            parsed = json.loads(text)
            return json.dumps(parsed, indent=2), "json"
        except json.JSONDecodeError:
            return text, "text"
    if lower.endswith(".md") or lower.endswith(".markdown"):
        return text, "markdown"
    return text, "text"


def _decode_request(body: DocumentParseRequest) -> Tuple[bytes, Optional[str]]:
    if body.content_base64:
        try:
            content = base64.b64decode(body.content_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(422, "content_base64 is not valid base64") from exc
        if len(content) > MAX_CONTENT_BYTES:
            raise HTTPException(413, "Document exceeds the 4MB limit")
        return content, "base64"
    if body.text is not None:
        if len(body.text) > MAX_DOCUMENT_CHARS:
            raise HTTPException(413, "Document exceeds the character limit")
        return body.text.encode("utf-8"), "text"
    raise HTTPException(422, "Provide either text or content_base64")


async def _summarize(settings: Settings, filename: str, text: str) -> Dict[str, Any]:
    client = get_client(settings)
    sample = text[:60_000]
    completion = await client.post_json(
        "/chat/completions",
        data={
            "model": settings.ASSISTANT_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Summarize the supplied document for a crypto token monitor. "
                        "Return strict JSON with keys summary (string, 2-4 sentences), "
                        "key_points (array of up to 8 short strings), and "
                        "risk_factors (array of short strings). Use only the document."
                    ),
                },
                {"role": "user", "content": f"Document: {filename}\n\n{sample}"},
            ],
            "max_tokens": 900,
            "temperature": 0.2,
            "venice_parameters": {
                "include_venice_system_prompt": False,
                "enable_web_search": "off",
            },
            "response_format": {"type": "json_object"},
        },
        timeout=90,
    )
    output = extract_chat_text(completion)
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"summary": output, "key_points": [], "risk_factors": []}


@router.post("/documents/parse")
@limiter.limit("20/hour")
async def parse_document(
    request: Request,
    body: DocumentParseRequest,
    settings: Settings = Depends(get_settings),
):
    """Parse a document and produce a structured summary."""
    content, input_kind = _decode_request(body)
    try:
        text, fmt = extract_document_text(body.filename, content)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    truncated = False
    if len(text) > MAX_DOCUMENT_CHARS:
        text = text[:MAX_DOCUMENT_CHARS]
        truncated = True
    try:
        summary = await _summarize(settings, body.filename, text)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Venice chat failed: {exc.response.status_code}") from exc
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise HTTPException(504, "Venice chat is temporarily unavailable") from exc
    return {
        "filename": body.filename,
        "format": fmt,
        "input_kind": input_kind,
        "characters": len(text),
        "truncated": truncated,
        "extracted_text": text,
        "summary": summary.get("summary") or "",
        "key_points": summary.get("key_points") or [],
        "risk_factors": summary.get("risk_factors") or [],
        "model": settings.ASSISTANT_MODEL,
        "note": "Model-generated summary; verify against the source document.",
    }


@router.post("/documents/ask")
@limiter.limit("30/hour")
async def ask_document(
    request: Request,
    body: DocumentAskRequest,
    settings: Settings = Depends(get_settings),
):
    """Answer a question grounded in a parsed document."""
    client = get_client(settings)
    sample = body.document_text[:60_000]
    try:
        completion = await client.post_json(
            "/chat/completions",
            data={
                "model": settings.ASSISTANT_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Answer using only the supplied document. If the answer is "
                            "not present, say so. Quote short supporting passages. Do not "
                            "give financial advice."
                        ),
                    },
                    {"role": "user", "content": f"Question: {body.question}\n\nDocument:\n{sample}"},
                ],
                "max_tokens": 800,
                "temperature": 0.2,
                "venice_parameters": {
                    "include_venice_system_prompt": False,
                    "enable_web_search": "off",
                },
            },
            timeout=90,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Venice chat failed: {exc.response.status_code}") from exc
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise HTTPException(504, "Venice chat is temporarily unavailable") from exc
    return {"answer": extract_chat_text(completion), "model": settings.ASSISTANT_MODEL}

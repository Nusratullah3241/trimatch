"""Turns a PDF into structured data using Gemini.

Free tier gives 20 requests/day PER MODEL, so this rotates through a pool
of models and moves to the next one whenever a quota runs out.
"""
import base64
import hashlib
import io
import json
from pathlib import Path

import google.generativeai as genai
from PIL import Image
from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.services import pdf_reader, prompts

genai.configure(api_key=settings.gemini_api_key)

# 20 requests/day each. Eight models = 160 requests/day, free.
MODEL_POOL = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
]

_models: dict = {}
_exhausted: set = set()

CACHE_DIR = Path("./data/extraction_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _get_model(name: str):
    if name not in _models:
        _models[name] = genai.GenerativeModel(
            name,
            system_instruction=prompts.EXTRACTION_SYSTEM,
            generation_config={"response_mime_type": "application/json"},
        )
    return _models[name]


def _generate(parts):
    """Tries each model in turn. Skips any that hit their daily quota."""
    last_error = None
    for name in MODEL_POOL:
        if name in _exhausted:
            continue
        try:
            return _get_model(name).generate_content(parts)
        except Exception as e:
            msg = str(e).lower()
            if "429" in msg or "quota" in msg or "exhausted" in msg:
                print(f"    [quota reached: {name} - switching]")
                _exhausted.add(name)
                last_error = e
                continue
            raise
    raise RuntimeError(
        f"All {len(MODEL_POOL)} models exhausted for today. "
        f"Cached results are kept - re-run tomorrow. Last error: {last_error}"
    )


class ExtractedLine(BaseModel):
    line_number: int = 0
    description: str = ""
    item_code: str | None = None
    quantity: float = 0
    unit_price: float | None = None
    line_total: float | None = None


class ExtractedDocument(BaseModel):
    document_number: str | None = None
    reference_po_number: str | None = None
    vendor_name: str | None = None
    document_date: str | None = None
    currency: str = "PKR"
    line_items: list[ExtractedLine] = Field(default_factory=list)
    subtotal: float | None = None
    tax: float | None = None
    grand_total: float | None = None
    confidence: float = 0.0
    was_scanned: bool = False
    raw_text: str = ""


def _cache_path(file_path: str, doc_type: str) -> Path:
    key = hashlib.md5(f"{file_path}|{doc_type}".encode()).hexdigest()
    return CACHE_DIR / f"{key}.json"


def _clean(raw: str) -> str:
    """Strips markdown fences if the model adds them anyway."""
    return raw.replace("```json", "").replace("```", "").strip()


def extract(file_path: str, doc_type: str, use_cache: bool = True) -> ExtractedDocument:
    """
    Reads one PDF and returns structured data.

    doc_type must be "PO", "GRN", or "INVOICE".
    """
    cache_file = _cache_path(file_path, doc_type)
    if use_cache and cache_file.exists():
        return ExtractedDocument(**json.loads(cache_file.read_text(encoding="utf-8")))

    text, was_scanned = pdf_reader.extract_text(file_path)

    if was_scanned:
        b64 = pdf_reader.page_to_base64(file_path)
        img = Image.open(io.BytesIO(base64.b64decode(b64)))
        parts = [img, prompts.extraction_user_prompt(doc_type, "[scanned image below]")]
    else:
        parts = [prompts.extraction_user_prompt(doc_type, text)]

    response = _generate(parts)
    raw = _clean(response.text)

    try:
        result = ExtractedDocument(**json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as err:
        # One retry, feeding the error back so the model can correct itself.
        retry = _generate(
            parts + [f"Your previous reply failed validation: {err}\n"
                     f"Return corrected JSON only."]
        )
        result = ExtractedDocument(**json.loads(_clean(retry.text)))

    result.was_scanned = was_scanned
    result.raw_text = text

    cache_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result
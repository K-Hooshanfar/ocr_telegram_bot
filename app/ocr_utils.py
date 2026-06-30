# app/ocr_utils.py

import warnings
import json
import re
import time
from google import genai
from pydantic import BaseModel
from .config import settings


class OCRResponse(BaseModel):
    raw_text: str    # either Markdown or LaTeX, depending on format_type
    direction: str   # "rtl" or "ltr"


def _detect_direction(text: str) -> str:
    """
    Heuristic: if >30% of letters are in Arabic/Hebrew ranges, assume RTL.
    """
    letters = re.findall(r"\w", text or "")
    if not letters:
        return "ltr"
    rtl = re.findall(
        r"[\u0590-\u05FF\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]", text
    )
    return "rtl" if (len(rtl) / len(letters)) > 0.3 else "ltr"


def perform_ocr_with_gemini(
    image_path: str,
    format_type: str = "markdown"
) -> dict:
    """
    OCR any document image using Gemini-2.0-Flash.
    Retries up to 3 times on failure (5s between attempts).
    format_type: "markdown" or "latex"
    Returns a dict:
      {
        "raw_text": "<string in requested format>",
        "direction": "rtl" or "ltr",
        # on total failure:
        "error": "OCR service unavailable, please try again later."
      }
    """
    # Normalize format_type
    fmt = format_type.lower()
    if fmt not in ("markdown", "latex"):
        fmt = "markdown"

    client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    # Static part of the prompt
    base_prompt = """
    You are an OCR assistant. Extract all text exactly as it appears in the image, preserving layout.
    - Use headings, paragraphs, lists, and tables to reflect columns or structured data.
    - If the document uses a multi-column layout, represent each column as a separate table or section.
    - Apply appropriate headings for titles and subheadings exactly as they appear.
    - Do not add any extra commentary, labels, or interpretation.
    """

    # Dynamic output instruction
    if fmt == "markdown":
        format_instruction = "Output *only* the raw extracted content formatted in **Markdown**."
    else:
        format_instruction = "Output *only* the raw extracted content formatted in **LaTeX**."

    # JSON wrapper instructions
    json_instructions = f"""
    {format_instruction}
    Finally, produce *only* a JSON object with two properties:
      • raw_text — the extracted text in {fmt.upper()}
      • direction — either "rtl" or "ltr" indicating text directionality
    Do not output anything else.
    """

    prompt = base_prompt + json_instructions

    last_exception = None
    for attempt in range(3):
        try:
            uploaded = client.files.upload(file=image_path)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[uploaded, prompt],
                config={
                    "response_mime_type": "application/json",
                    "response_schema": OCRResponse,
                },
            )

            # Try typed parse first
            parsed = getattr(response, "parsed", None)
            if parsed:
                data = parsed.model_dump()
            else:
                # Fallback to JSON parse
                try:
                    data = json.loads(response.text)
                except json.JSONDecodeError:
                    # Last resort: treat whole text as raw_text
                    data = {
                        "raw_text": response.text.strip(),
                        "direction": _detect_direction(response.text),
                    }

            # Validate direction
            data["direction"] = (
                data.get("direction")
                if data.get("direction") in ("rtl", "ltr")
                else _detect_direction(data.get("raw_text", ""))
            )

            return data

        except Exception as exc:
            last_exception = exc
            warnings.warn(f"Gemini OCR attempt {attempt + 1} failed: {exc}")
            if attempt < 2:
                time.sleep(5)
            else:
                # After 3 failures
                return {
                    "raw_text": "",
                    "direction": "ltr",
                    "error": "OCR service unavailable, please try again later."
                }

    # Fallback guard
    return {
        "raw_text": "",
        "direction": "ltr",
        "error": f"OCR failed: {last_exception}"
    }

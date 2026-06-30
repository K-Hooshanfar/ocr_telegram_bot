# app/routes/ocr.py

import os
import uuid
import re
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Query
from sqlalchemy.orm import Session

from .. import auth, models
from ..ocr_utils import perform_ocr_with_gemini
from ..util_convert import markdown_to_docx

router = APIRouter()
UPLOAD_DIR = "app/static/upload"
DOCX_DIR   = os.path.join(UPLOAD_DIR, "docs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DOCX_DIR, exist_ok=True)


def _detect_direction(text: str) -> str:
    letters = re.findall(r"\w", text or "")
    if not letters:
        return "ltr"
    rtl = re.findall(
        r"[\u0590-\u05FF\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]", text
    )
    return "rtl" if (len(rtl) / len(letters)) > 0.3 else "ltr"


def _extract_hash(fn: str) -> str:
    return fn.split("_", 1)[0]


@router.post("/upload")
def upload_ocr(
    file: UploadFile = File(...),
    format_type: str = Query(
        "markdown",
        description="Output format: 'markdown' or 'latex'",
        regex="^(markdown|latex)$"
    ),
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    # 1) Credit check
    if not current_user.is_admin and current_user.credits <= 0:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="No remaining credits")

    # 2) Save upload
    unique = f"{uuid.uuid4().hex}_{file.filename}"
    img_path = os.path.join(UPLOAD_DIR, unique)
    with open(img_path, "wb") as buf:
        buf.write(file.file.read())

    # 3) OCR
    ocr_res = perform_ocr_with_gemini(img_path, format_type=format_type)
    if "error" in ocr_res:
        os.remove(img_path)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=ocr_res["error"])

    raw = ocr_res.get("raw_text", "").strip()
    if not raw:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail="OCR returned no text. Try again later.")

    direction = ocr_res.get("direction") or _detect_direction(raw)
    record_hash = _extract_hash(unique)

    # 4) Debit credit
    if not current_user.is_admin:
        current_user.credits -= 1
        db.add(current_user)

    # 5) Optional DOCX conversion
    docx_url = None
    if format_type == "markdown":
        # convert & save alongside images
        out_docx = os.path.join(DOCX_DIR, f"{record_hash}.docx")
        markdown_to_docx(raw, out_path=out_docx, is_rtl=(direction=="rtl"))
        docx_url = f"/static/upload/docs/{record_hash}.docx"

    # 6) Persist
    req = models.OCRRequest(
        image_path=img_path,
        original_filename=file.filename,
        direction=direction,
        result_text=raw,
        docx_path=docx_url,
        user_id=None if current_user.is_admin else current_user.id,
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    # 7) Return
    resp = {
        "message": "OCR successful.",
        "format": format_type,
        "raw_text": raw,
        "direction": direction,
        "remaining_credits": (current_user.credits
                              if not current_user.is_admin else "Unlimited"),
        "image_url": f"/static/upload/{unique}",
        "id": req.id,
        "hash": record_hash,
    }
    if docx_url:
        resp["docx_url"] = docx_url
    return resp


@router.get("/history")
def get_ocr_history(
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    qs = db.query(models.OCRRequest)
    if not current_user.is_admin:
        qs = qs.filter(models.OCRRequest.user_id == current_user.id)

    results = []
    for r in qs.all():
        fn = os.path.basename(r.image_path)
        h  = _extract_hash(fn)
        results.append({
            "id": r.id,
            "hash": h,
            "filename": r.original_filename,
            "direction": r.direction,
            "format": "markdown",            # default
            "raw_text": r.result_text,
            "image_url": f"/static/upload/{fn}",
            "timestamp": r.created_at.isoformat(),
            "docx_url": r.docx_path,         # may be None
        })
    return results


@router.get("/history/{record_hash}")
def get_ocr_by_hash(
    record_hash: str,
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    # find by filename prefix
    entry = None
    for r in db.query(models.OCRRequest).all():
        if os.path.basename(r.image_path).startswith(record_hash + "_"):
            entry = r
            break

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Record not found")
    if not current_user.is_admin and entry.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not allowed")

    fn = os.path.basename(entry.image_path)
    return {
        "id": entry.id,
        "hash": record_hash,
        "filename": entry.original_filename,
        "direction": entry.direction,
        "format": "markdown",
        "raw_text": entry.result_text,
        "image_url": f"/static/upload/{fn}",
        "timestamp": entry.created_at.isoformat(),
        "docx_url": entry.docx_path,
    }


@router.delete("/history/{ocr_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ocr_history(
    ocr_id: int,
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    req = db.query(models.OCRRequest).filter(models.OCRRequest.id == ocr_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Record not found")
    if not current_user.is_admin and req.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not allowed")
    try:
        os.remove(req.image_path)
        if req.docx_path:
            # remove DOCX too
            os.remove(os.path.join("app", req.docx_path.lstrip("/")))
    except OSError:
        pass
    db.delete(req)
    db.commit()
    return
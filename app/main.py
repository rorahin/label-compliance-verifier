from io import BytesIO
import time

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image, UnidentifiedImageError

from app.ocr import extract_text_from_bytes
from app.parser import (
    extract_abv,
    extract_net_contents,
    detect_government_warning,
)
from app.validator import validate_label


app = FastAPI(title="Alcohol Label Verification")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")


MAX_UPLOAD_BYTES = 10 * 1024 * 1024

ALLOWED_IMAGE_FORMATS = {
    "JPEG",
    "PNG",
    "WEBP",
}


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.post("/verify")
async def verify_label(
    request: Request,
    brand_name: str = Form(...),
    class_type: str = Form(...),
    alcohol_content: str = Form(...),
    net_contents: str = Form(...),
    label_image: UploadFile = File(...),
):
    request_start = time.perf_counter()

    # Read the uploaded image into memory only.
    # The label is not intentionally written to disk.
    file_bytes = await label_image.read(MAX_UPLOAD_BYTES + 1)

    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Image must be 10 MB or smaller.",
        )

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    # Validate the uploaded image before running OCR.
    try:
        image = Image.open(BytesIO(file_bytes))

        image_format = image.format
        width, height = image.size

        image.verify()

    except (UnidentifiedImageError, OSError):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid image.",
        )

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG, and WebP images are supported.",
        )

    # Run OCR.
    try:
        ocr_result = extract_text_from_bytes(file_bytes)

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="The label image could not be processed.",
        )

    # Combine OCR lines into a single text block.
    ocr_text = " ".join(
        line["text"]
        for line in ocr_result["lines"]
    )

    # Extract structured information from the OCR text.
    parsed = {
        "abv": extract_abv(ocr_text),

        "net_contents_ml": extract_net_contents(
            ocr_text
        ),

        "government_warning_found": (
            detect_government_warning(
                ocr_text
            )
        ),
    }

    # Compare application information with the label.
    validation = validate_label(
        brand_name=brand_name,
        class_type=class_type,
        alcohol_content=alcohol_content,
        net_contents=net_contents,
        ocr_text=ocr_text,
        parsed=parsed,
    )

    request_seconds = time.perf_counter() - request_start

    # Render a human-readable result page.
    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={
            "overall_status": validation["overall_status"],
            "validation": validation["fields"],

            "application": {
                "brand_name": brand_name,
                "class_type": class_type,
                "alcohol_content": alcohol_content,
                "net_contents": net_contents,
            },

            "detected": {
                "abv": parsed["abv"],
                "net_contents_ml": parsed["net_contents_ml"],
                "government_warning_found": (
                    parsed["government_warning_found"]
                ),
            },

            "ocr_text": ocr_text,

            "ocr_inference_seconds": round(
                ocr_result["inference_seconds"],
                3,
            ),

            "ocr_total_seconds": round(
                ocr_result["total_seconds"],
                3,
            ),

            "request_seconds": round(
                request_seconds,
                3,
            ),

            "image": {
                "filename": label_image.filename,
                "format": image_format,
                "width": width,
                "height": height,
                "size_bytes": len(file_bytes),
            },
        },
    )
import time

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import MAX_UPLOAD_BYTES
from app.observability import (
    REQUEST_ID_HEADER,
    get_request_id,
    logger,
)
from app.ocr import extract_text_from_bytes
from app.parser import (
    detect_government_warning,
    extract_abv,
    extract_net_contents,
)
from app.security import validate_image_bytes
from app.security_headers import apply_security_headers
from app.validator import validate_label

app = FastAPI(title="Alcohol Label Verification")

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)

templates = Jinja2Templates(directory="app/templates")


@app.middleware("http")
async def security_headers_middleware(
    request: Request,
    call_next,
):
    response = await call_next(request)

    return apply_security_headers(response)


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
):
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "message": str(exc.detail),
        },
        status_code=exc.status_code,
    )


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next,
):
    request_id = get_request_id(request.headers.get(REQUEST_ID_HEADER))

    start = time.perf_counter()

    try:
        response = await call_next(request)

    except Exception:
        duration_ms = (time.perf_counter() - start) * 1000

        logger.exception(
            "request_failed request_id=%s method=%s path=%s duration_ms=%.1f",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
        )

        raise

    duration_ms = (time.perf_counter() - start) * 1000

    response.headers[REQUEST_ID_HEADER] = request_id

    logger.info(
        "request_completed "
        "request_id=%s "
        "method=%s "
        "path=%s "
        "status=%s "
        "duration_ms=%.1f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    return response


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

    # Read only into memory.
    # One extra byte allows us to detect oversized uploads.
    file_bytes = await label_image.read(MAX_UPLOAD_BYTES + 1)

    # Perform centralized security validation.
    # This verifies:
    # - non-empty upload
    # - maximum encoded size
    # - actual image format
    # - decoded pixel dimensions
    # - malformed images
    # - decompression-bomb conditions
    image_info = validate_image_bytes(file_bytes)

    image_format = image_info["format"]
    width = image_info["width"]
    height = image_info["height"]

    # Run OCR entirely in memory.
    try:
        ocr_result = extract_text_from_bytes(file_bytes)

    except Exception:
        raise HTTPException(
            status_code=500,
            detail=("The label image could not be processed."),
        )

    # Combine recognized OCR lines into one text block.
    ocr_text = " ".join(line["text"] for line in ocr_result["lines"])

    # Extract structured values from OCR text.
    parsed = {
        "abv": extract_abv(ocr_text),
        "net_contents_ml": extract_net_contents(ocr_text),
        "government_warning_found": (detect_government_warning(ocr_text)),
    }

    # Compare application values against label values.
    # OCR line confidence is included so uncertain
    # results can be routed to REVIEW.
    validation = validate_label(
        brand_name=brand_name,
        class_type=class_type,
        alcohol_content=alcohol_content,
        net_contents=net_contents,
        ocr_text=ocr_text,
        parsed=parsed,
        ocr_lines=ocr_result["lines"],
    )

    request_seconds = time.perf_counter() - request_start

    # Render reviewer-friendly result page.
    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={
            "overall_status": (validation["overall_status"]),
            "validation": (validation["fields"]),
            "application": {
                "brand_name": brand_name,
                "class_type": class_type,
                "alcohol_content": alcohol_content,
                "net_contents": net_contents,
            },
            "detected": {
                "abv": parsed["abv"],
                "net_contents_ml": (parsed["net_contents_ml"]),
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
                "filename": (label_image.filename),
                "format": image_format,
                "width": width,
                "height": height,
                "size_bytes": (image_info["size_bytes"]),
                "pixel_count": (image_info["pixel_count"]),
            },
        },
    )

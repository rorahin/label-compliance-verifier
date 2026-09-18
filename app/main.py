import time

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
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
async def home(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


async def process_uploaded_image(
    upload: UploadFile,
) -> dict:
    """
    Validate and OCR one uploaded label image.

    Image contents remain in memory and are not
    intentionally persisted to disk.
    """
    file_bytes = await upload.read(MAX_UPLOAD_BYTES + 1)

    image_info = validate_image_bytes(file_bytes)

    try:
        ocr_result = extract_text_from_bytes(file_bytes)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=("One of the label images could not be processed."),
        ) from exc

    return {
        "filename": upload.filename,
        "image_info": image_info,
        "ocr": ocr_result,
    }


def build_image_context(
    processed_image: dict,
) -> dict:
    """
    Build non-content image metadata for the
    result template.
    """
    image_info = processed_image["image_info"]

    return {
        "filename": processed_image["filename"],
        "format": image_info["format"],
        "width": image_info["width"],
        "height": image_info["height"],
        "size_bytes": image_info["size_bytes"],
        "pixel_count": image_info["pixel_count"],
    }


@app.post("/verify")
async def verify_label(
    request: Request,
    brand_name: str = Form(...),
    class_type: str = Form(...),
    alcohol_content: str = Form(...),
    net_contents: str = Form(...),
    label_image: UploadFile = File(...),
    additional_label_image: (UploadFile | None) = File(None),
):
    request_start = time.perf_counter()

    # Primary label image.
    primary_result = await process_uploaded_image(label_image)

    processed_images = [primary_result]

    # Optional back or secondary label.
    if additional_label_image is not None and additional_label_image.filename:
        additional_result = await process_uploaded_image(
            additional_label_image
        )

        processed_images.append(additional_result)

    # Combine OCR evidence from all supplied
    # images for the same product.
    combined_lines = []

    for processed_image in processed_images:
        combined_lines.extend(processed_image["ocr"]["lines"])

    ocr_text = " ".join(line["text"] for line in combined_lines)

    # Extract structured values from the
    # combined OCR evidence.
    parsed = {
        "abv": extract_abv(ocr_text),
        "net_contents_ml": (extract_net_contents(ocr_text)),
        "government_warning_found": (detect_government_warning(ocr_text)),
    }

    # Compare the submitted application data
    # against evidence from all label images.
    validation = validate_label(
        brand_name=brand_name,
        class_type=class_type,
        alcohol_content=alcohol_content,
        net_contents=net_contents,
        ocr_text=ocr_text,
        parsed=parsed,
        ocr_lines=combined_lines,
    )

    total_inference_seconds = sum(
        processed_image["ocr"]["inference_seconds"]
        for processed_image in processed_images
    )

    total_ocr_seconds = sum(
        processed_image["ocr"]["total_seconds"]
        for processed_image in processed_images
    )

    request_seconds = time.perf_counter() - request_start

    primary_image_context = build_image_context(primary_result)

    additional_image_context = None

    if len(processed_images) == 2:
        additional_image_context = build_image_context(processed_images[1])

    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={
            "overall_status": (validation["overall_status"]),
            "validation": (validation["fields"]),
            "application": {
                "brand_name": (brand_name),
                "class_type": (class_type),
                "alcohol_content": (alcohol_content),
                "net_contents": (net_contents),
            },
            "detected": {
                "abv": (parsed["abv"]),
                "net_contents_ml": (parsed["net_contents_ml"]),
                "government_warning_found": (
                    parsed["government_warning_found"]
                ),
            },
            "ocr_text": ocr_text,
            "ocr_inference_seconds": round(
                total_inference_seconds,
                3,
            ),
            "ocr_total_seconds": round(
                total_ocr_seconds,
                3,
            ),
            "request_seconds": round(
                request_seconds,
                3,
            ),
            "image_count": len(processed_images),
            "image": (primary_image_context),
            "additional_image": (additional_image_context),
        },
    )

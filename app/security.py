import warnings
from io import BytesIO

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

from app.config import (
    ALLOWED_IMAGE_FORMATS,
    MAX_IMAGE_PIXELS,
    MAX_UPLOAD_BYTES,
)


def validate_image_bytes(file_bytes: bytes) -> dict:
    """
    Validate an uploaded image before OCR processing.

    Security controls:
    - reject empty files
    - enforce maximum encoded file size
    - verify actual decoded image format
    - enforce maximum decoded pixel count
    - detect malformed images
    - detect Pillow decompression-bomb conditions

    The image remains in memory and is not written to disk.
    """

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Image must be 10 MB or smaller.",
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter(
                "error",
                Image.DecompressionBombWarning,
            )

            image = Image.open(BytesIO(file_bytes))

            image_format = image.format
            width, height = image.size

            if image_format not in ALLOWED_IMAGE_FORMATS:
                raise HTTPException(
                    status_code=400,
                    detail=("Only JPG, PNG, and WebP images are supported."),
                )

            if width <= 0 or height <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="The image dimensions are invalid.",
                )

            pixel_count = width * height

            if pixel_count > MAX_IMAGE_PIXELS:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        "Image dimensions are too large. "
                        "Please upload an image under "
                        "25 megapixels."
                    ),
                )

            image.verify()

    except HTTPException:
        raise

    except (
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
    ):
        raise HTTPException(
            status_code=413,
            detail="Image dimensions are unsafe to process.",
        )

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
    ):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid image.",
        )

    return {
        "format": image_format,
        "width": width,
        "height": height,
        "size_bytes": len(file_bytes),
        "pixel_count": pixel_count,
    }

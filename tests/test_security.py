from io import BytesIO

import pytest
from fastapi import HTTPException
from PIL import Image

import app.security as security
from app.config import MAX_UPLOAD_BYTES
from app.security import validate_image_bytes


def make_image_bytes(
    image_format="PNG",
    size=(100, 100),
):
    """
    Create a small in-memory image for security tests.
    """
    image = Image.new(
        "RGB",
        size,
        "white",
    )

    buffer = BytesIO()

    image.save(
        buffer,
        format=image_format,
    )

    return buffer.getvalue()


def test_valid_png_is_accepted():
    image_bytes = make_image_bytes(image_format="PNG")

    result = validate_image_bytes(image_bytes)

    assert result["format"] == "PNG"
    assert result["width"] == 100
    assert result["height"] == 100
    assert result["pixel_count"] == 10_000


def test_empty_upload_is_rejected():
    with pytest.raises(HTTPException) as error:
        validate_image_bytes(b"")

    assert error.value.status_code == 400
    assert "empty" in error.value.detail.lower()


def test_fake_image_is_rejected():
    """
    Simulates a malicious/non-image file renamed to .png.

    Validation uses actual file contents rather than trusting
    the filename or extension.
    """
    fake_image = b"This is not actually a PNG image."

    with pytest.raises(HTTPException) as error:
        validate_image_bytes(fake_image)

    assert error.value.status_code == 400


def test_oversized_file_is_rejected():
    oversized_payload = b"x" * (MAX_UPLOAD_BYTES + 1)

    with pytest.raises(HTTPException) as error:
        validate_image_bytes(oversized_payload)

    assert error.value.status_code == 413


def test_unsupported_image_format_is_rejected():
    bmp_bytes = make_image_bytes(image_format="BMP")

    with pytest.raises(HTTPException) as error:
        validate_image_bytes(bmp_bytes)

    assert error.value.status_code == 400
    assert "JPG" in error.value.detail


def test_excessive_pixel_count_is_rejected(
    monkeypatch,
):
    """
    Use a deliberately low test limit so we can verify
    dimension-based DoS protection without creating a
    genuinely huge image.
    """
    monkeypatch.setattr(
        security,
        "MAX_IMAGE_PIXELS",
        100,
    )

    image_bytes = make_image_bytes(
        image_format="PNG",
        size=(20, 20),
    )

    with pytest.raises(HTTPException) as error:
        validate_image_bytes(image_bytes)

    assert error.value.status_code == 413
    assert "megapixels" in error.value.detail.lower()

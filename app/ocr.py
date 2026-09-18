import time
from io import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageOps
from rapidocr import RapidOCR


# Load OCR models once when the server starts.
ocr_engine = RapidOCR()

# Large images slow OCR without necessarily improving recognition.
MAX_IMAGE_DIMENSION = 1600


def prepare_image(image_bytes: bytes):
    """
    Decode and normalize an uploaded image entirely in memory.
    Large images are resized while preserving aspect ratio.
    """
    image = Image.open(BytesIO(image_bytes))

    # Correct camera/phone orientation.
    image = ImageOps.exif_transpose(image)

    # Normalize color mode.
    image = image.convert("RGB")

    width, height = image.size
    largest_dimension = max(width, height)

    if largest_dimension > MAX_IMAGE_DIMENSION:
        scale = MAX_IMAGE_DIMENSION / largest_dimension

        new_width = int(width * scale)
        new_height = int(height * scale)

        image = image.resize(
            (new_width, new_height),
            Image.Resampling.LANCZOS
        )

    return image


def extract_text_from_bytes(image_bytes: bytes):
    """
    Extract OCR text from image bytes without writing the image to disk.
    """
    start = time.perf_counter()

    image = prepare_image(image_bytes)

    processed_width, processed_height = image.size

    # Convert PIL RGB image to OpenCV BGR format.
    image_array = np.array(image)

    image_array = cv2.cvtColor(
        image_array,
        cv2.COLOR_RGB2BGR
    )

    result = ocr_engine(image_array)

    total_time = time.perf_counter() - start

    lines = []

    if result.txts:
        for text, score in zip(
            result.txts,
            result.scores
        ):
            lines.append({
                "text": text,
                "confidence": float(score)
            })

    return {
        "lines": lines,
        "inference_seconds": float(result.elapse),
        "total_seconds": total_time,
        "processed_width": processed_width,
        "processed_height": processed_height,
    }

# Application configuration

# Maximum uploaded file size: 10 MB.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# Maximum number of decoded pixels accepted from an image.
# 25 MP is more than sufficient for label verification while
# limiting memory and CPU exposure from malicious images.
MAX_IMAGE_PIXELS = 25_000_000

# Maximum dimension used for OCR processing.
# Larger valid images are resized before OCR.
MAX_IMAGE_DIMENSION = 1600

# OCR results below this confidence are routed to REVIEW.
#
# This model score is used only as an uncertainty signal.
# It is not interpreted as a regulatory probability.
MIN_OCR_CONFIDENCE = 0.85

# Supported formats after actual image decoding.
ALLOWED_IMAGE_FORMATS = {
    "JPEG",
    "PNG",
    "WEBP",
}

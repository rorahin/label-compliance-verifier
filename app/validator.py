import re
from pathlib import Path

from app.parser import (
    extract_abv,
    extract_government_warning,
    extract_net_contents,
    normalize_text,
)

WARNING_REFERENCE_PATH = (
    Path(__file__).resolve().parent / "warning_reference.txt"
)


def normalize_for_comparison(text: str) -> str:
    """
    Normalize text for comparison while preserving apostrophes.
    """
    text = normalize_text(text)
    text = re.sub(r"[^A-Z0-9']+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def has_low_confidence_line(ocr_lines) -> bool:
    """
    Return True if any OCR line was marked low-confidence.
    """
    if not ocr_lines:
        return False

    return any(line.get("low_confidence", False) for line in ocr_lines)


def text_field_is_low_confidence(
    expected: str,
    ocr_lines,
) -> bool:
    """
    Determine whether the OCR line containing an expected
    text value was marked low-confidence.
    """
    if not ocr_lines:
        return False

    expected_normalized = normalize_for_comparison(expected)

    for line in ocr_lines:
        line_normalized = normalize_for_comparison(line.get("text", ""))

        if expected_normalized in line_normalized:
            return line.get("low_confidence", False)

    return False


def abv_is_low_confidence(
    detected_abv,
    ocr_lines,
) -> bool:
    """
    Determine whether the OCR line containing the detected ABV
    was marked low-confidence.
    """
    if detected_abv is None or not ocr_lines:
        return False

    for line in ocr_lines:
        line_abv = extract_abv(line.get("text", ""))

        if line_abv is not None and abs(line_abv - detected_abv) < 0.01:
            return line.get("low_confidence", False)

    return False


def net_contents_is_low_confidence(
    detected_ml,
    ocr_lines,
) -> bool:
    """
    Determine whether the OCR line containing net contents
    was marked low-confidence.
    """
    if detected_ml is None or not ocr_lines:
        return False

    for line in ocr_lines:
        line_value = extract_net_contents(line.get("text", ""))

        if line_value is not None and abs(line_value - detected_ml) < 0.01:
            return line.get("low_confidence", False)

    return False


def warning_is_low_confidence(ocr_lines) -> bool:
    """
    Check OCR confidence for the Government Warning section.
    """
    if not ocr_lines:
        return False

    warning_started = False

    for line in ocr_lines:
        text = normalize_text(line.get("text", ""))

        if "GOVERNMENT WARNING:" in text:
            warning_started = True

        if warning_started and line.get("low_confidence", False):
            return True

    return False


def validate_text_field(
    expected: str,
    ocr_text: str,
    ocr_lines=None,
):
    """
    Check whether an expected text value appears on the label.
    Low-confidence OCR is routed to manual review.
    """
    expected_normalized = normalize_for_comparison(expected)
    ocr_normalized = normalize_for_comparison(ocr_text)

    if not expected_normalized:
        return {
            "status": "REVIEW",
            "message": "Expected value is missing.",
        }

    if expected_normalized in ocr_normalized:
        if text_field_is_low_confidence(
            expected,
            ocr_lines,
        ):
            return {
                "status": "REVIEW",
                "message": (
                    "Value appears to match, but OCR confidence "
                    "is too low for automatic verification."
                ),
            }

        return {
            "status": "PASS",
            "message": "Value matches the label.",
        }

    if has_low_confidence_line(ocr_lines):
        return {
            "status": "REVIEW",
            "message": (
                "Expected value could not be confidently verified "
                "from the label."
            ),
        }

    return {
        "status": "FAIL",
        "message": "Expected value was not found on the label.",
    }


def validate_abv(
    expected_text: str,
    detected_abv,
    ocr_lines=None,
):
    """
    Compare application ABV with detected label ABV.

    Low-confidence OCR produces REVIEW instead of an
    automatic compliance decision.
    """
    expected_abv = extract_abv(expected_text)

    if expected_abv is None:
        return {
            "status": "REVIEW",
            "expected": None,
            "detected": detected_abv,
            "message": "Application ABV could not be interpreted.",
        }

    if detected_abv is None:
        return {
            "status": "REVIEW",
            "expected": expected_abv,
            "detected": None,
            "message": "Alcohol content could not be read from the label.",
        }

    low_confidence = abv_is_low_confidence(
        detected_abv,
        ocr_lines,
    )

    if low_confidence:
        return {
            "status": "REVIEW",
            "expected": expected_abv,
            "detected": detected_abv,
            "message": (
                "Alcohol content was detected with low OCR "
                "confidence and requires manual review."
            ),
        }

    if abs(expected_abv - detected_abv) < 0.01:
        return {
            "status": "PASS",
            "expected": expected_abv,
            "detected": detected_abv,
            "message": "Alcohol content matches.",
        }

    return {
        "status": "FAIL",
        "expected": expected_abv,
        "detected": detected_abv,
        "message": "Alcohol content does not match.",
    }


def validate_net_contents(
    expected_text: str,
    detected_ml,
    ocr_lines=None,
):
    """
    Compare expected and detected net contents.
    """
    expected_ml = extract_net_contents(expected_text)

    if expected_ml is None:
        return {
            "status": "REVIEW",
            "expected_ml": None,
            "detected_ml": detected_ml,
            "message": ("Application net contents could not be interpreted."),
        }

    if detected_ml is None:
        return {
            "status": "REVIEW",
            "expected_ml": expected_ml,
            "detected_ml": None,
            "message": ("Net contents could not be read from the label."),
        }

    low_confidence = net_contents_is_low_confidence(
        detected_ml,
        ocr_lines,
    )

    if low_confidence:
        return {
            "status": "REVIEW",
            "expected_ml": expected_ml,
            "detected_ml": detected_ml,
            "message": (
                "Net contents were detected with low OCR "
                "confidence and require manual review."
            ),
        }

    if abs(expected_ml - detected_ml) < 0.01:
        return {
            "status": "PASS",
            "expected_ml": expected_ml,
            "detected_ml": detected_ml,
            "message": "Net contents match.",
        }

    return {
        "status": "FAIL",
        "expected_ml": expected_ml,
        "detected_ml": detected_ml,
        "message": "Net contents do not match.",
    }


def load_warning_reference():
    """
    Load the official Government Warning reference.
    """
    try:
        return WARNING_REFERENCE_PATH.read_text(encoding="utf-8").strip()

    except OSError:
        return None


def validate_warning(
    ocr_text: str,
    ocr_lines=None,
):
    """
    Validate OCR-readable Government Warning wording.

    Visual formatting such as bold type, type size,
    contrast, and placement remain outside the prototype.
    """
    expected_warning = load_warning_reference()

    if not expected_warning:
        return {
            "status": "REVIEW",
            "message": ("Government Warning reference could not be loaded."),
        }

    actual_warning = extract_government_warning(ocr_text)

    if actual_warning is None:
        if has_low_confidence_line(ocr_lines):
            return {
                "status": "REVIEW",
                "message": (
                    "Government Warning could not be confidently "
                    "read from the label."
                ),
            }

        return {
            "status": "FAIL",
            "message": "Government Warning was not found.",
        }

    if warning_is_low_confidence(ocr_lines):
        return {
            "status": "REVIEW",
            "message": (
                "Government Warning was detected, but OCR "
                "confidence is too low for automatic verification."
            ),
        }

    expected_normalized = normalize_text(expected_warning)

    actual_normalized = normalize_text(actual_warning)

    if expected_normalized not in actual_normalized:
        return {
            "status": "FAIL",
            "message": (
                "Government Warning wording does not match the required text."
            ),
        }

    return {
        "status": "PASS",
        "message": "Government Warning wording matches.",
        "formatting_note": (
            "Bold type, type size, contrast, and placement "
            "are not verified by this prototype."
        ),
    }


def determine_overall_status(fields: dict) -> str:
    """
    FAIL takes priority over REVIEW.
    REVIEW takes priority over PASS.
    """
    statuses = [result["status"] for result in fields.values()]

    if "FAIL" in statuses:
        return "FAIL"

    if "REVIEW" in statuses:
        return "REVIEW"

    return "PASS"


def validate_label(
    brand_name: str,
    class_type: str,
    alcohol_content: str,
    net_contents: str,
    ocr_text: str,
    parsed: dict,
    ocr_lines=None,
):
    """
    Compare application information against OCR label data.
    """
    fields = {
        "brand_name": validate_text_field(
            brand_name,
            ocr_text,
            ocr_lines,
        ),
        "class_type": validate_text_field(
            class_type,
            ocr_text,
            ocr_lines,
        ),
        "alcohol_content": validate_abv(
            alcohol_content,
            parsed.get("abv"),
            ocr_lines,
        ),
        "net_contents": validate_net_contents(
            net_contents,
            parsed.get("net_contents_ml"),
            ocr_lines,
        ),
        "government_warning": validate_warning(
            ocr_text,
            ocr_lines,
        ),
    }

    return {
        "overall_status": determine_overall_status(fields),
        "fields": fields,
    }

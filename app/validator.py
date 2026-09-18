import re
from pathlib import Path

from app.parser import (
    normalize_text,
    extract_abv,
    extract_net_contents,
    extract_government_warning,
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


def validate_text_field(expected: str, ocr_text: str):
    """
    Check whether an expected text value appears on the label.
    """
    expected_normalized = normalize_for_comparison(expected)
    ocr_normalized = normalize_for_comparison(ocr_text)

    if not expected_normalized:
        return {
            "status": "REVIEW",
            "message": "Expected value is missing."
        }

    if expected_normalized in ocr_normalized:
        return {
            "status": "PASS",
            "message": "Value matches the label."
        }

    return {
        "status": "FAIL",
        "message": "Expected value was not found on the label."
    }


def validate_abv(expected_text: str, detected_abv):
    """
    Compare expected application ABV with detected label ABV.
    """
    expected_abv = extract_abv(expected_text)

    if expected_abv is None:
        return {
            "status": "REVIEW",
            "expected": None,
            "detected": detected_abv,
            "message": "Application ABV could not be interpreted."
        }

    if detected_abv is None:
        return {
            "status": "REVIEW",
            "expected": expected_abv,
            "detected": None,
            "message": "Alcohol content could not be read from the label."
        }

    if abs(expected_abv - detected_abv) < 0.01:
        return {
            "status": "PASS",
            "expected": expected_abv,
            "detected": detected_abv,
            "message": "Alcohol content matches."
        }

    return {
        "status": "FAIL",
        "expected": expected_abv,
        "detected": detected_abv,
        "message": "Alcohol content does not match."
    }


def validate_net_contents(expected_text: str, detected_ml):
    """
    Compare expected and detected net contents in milliliters.
    """
    expected_ml = extract_net_contents(expected_text)

    if expected_ml is None:
        return {
            "status": "REVIEW",
            "expected_ml": None,
            "detected_ml": detected_ml,
            "message": "Application net contents could not be interpreted."
        }

    if detected_ml is None:
        return {
            "status": "REVIEW",
            "expected_ml": expected_ml,
            "detected_ml": None,
            "message": "Net contents could not be read from the label."
        }

    if abs(expected_ml - detected_ml) < 0.01:
        return {
            "status": "PASS",
            "expected_ml": expected_ml,
            "detected_ml": detected_ml,
            "message": "Net contents match."
        }

    return {
        "status": "FAIL",
        "expected_ml": expected_ml,
        "detected_ml": detected_ml,
        "message": "Net contents do not match."
    }


def load_warning_reference():
    """
    Load the official warning reference text.
    """
    try:
        return WARNING_REFERENCE_PATH.read_text(
            encoding="utf-8"
        ).strip()

    except OSError:
        return None


def validate_warning(ocr_text: str):
    """
    Validate the Government Warning wording.

    This verifies OCR-readable wording only.
    Bold type, type size, contrast, and placement
    remain outside the current prototype.
    """
    expected_warning = load_warning_reference()

    if not expected_warning:
        return {
            "status": "REVIEW",
            "message": "Government Warning reference could not be loaded."
        }

    actual_warning = extract_government_warning(ocr_text)

    if actual_warning is None:
        return {
            "status": "FAIL",
            "message": "Government Warning was not found."
        }

    expected_normalized = normalize_text(expected_warning)
    actual_normalized = normalize_text(actual_warning)

    if expected_normalized not in actual_normalized:
        return {
            "status": "FAIL",
            "message": (
                "Government Warning wording does not match "
                "the required text."
            )
        }

    return {
        "status": "PASS",
        "message": "Government Warning wording matches.",
        "formatting_note": (
            "Bold type, type size, contrast, and placement "
            "are not verified by this prototype."
        )
    }


def determine_overall_status(fields: dict) -> str:
    """
    Determine the overall label result.
    """
    statuses = [
        result["status"]
        for result in fields.values()
    ]

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
):
    """
    Compare application information against the OCR label data.
    """
    fields = {
        "brand_name": validate_text_field(
            brand_name,
            ocr_text
        ),

        "class_type": validate_text_field(
            class_type,
            ocr_text
        ),

        "alcohol_content": validate_abv(
            alcohol_content,
            parsed.get("abv")
        ),

        "net_contents": validate_net_contents(
            net_contents,
            parsed.get("net_contents_ml")
        ),

        "government_warning": validate_warning(
            ocr_text
        ),
    }

    return {
        "overall_status": determine_overall_status(fields),
        "fields": fields,
    }

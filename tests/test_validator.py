from app.validator import (
    determine_overall_status,
    validate_abv,
    validate_net_contents,
    validate_text_field,
    validate_warning,
)

VALID_WARNING = (
    "GOVERNMENT WARNING: "
    "(1) According to the Surgeon General, women should not drink "
    "alcoholic beverages during pregnancy because of the risk of "
    "birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability "
    "to drive a car or operate machinery, and may cause health problems."
)


def test_brand_name_passes_case_difference():
    result = validate_text_field(
        "Stone's Throw",
        "STONE'S THROW Kentucky Straight Bourbon Whiskey",
    )

    assert result["status"] == "PASS"


def test_brand_name_fails_when_missing():
    result = validate_text_field(
        "OLD TOM DISTILLERY",
        "SOME OTHER DISTILLERY",
    )

    assert result["status"] == "FAIL"


def test_abv_pass():
    result = validate_abv("45%", 45.0)

    assert result["status"] == "PASS"


def test_abv_fail():
    result = validate_abv("40%", 45.0)

    assert result["status"] == "FAIL"


def test_abv_review_when_not_detected():
    result = validate_abv("45%", None)

    assert result["status"] == "REVIEW"


def test_net_contents_pass_same_units():
    result = validate_net_contents("750 mL", 750)

    assert result["status"] == "PASS"


def test_net_contents_pass_equivalent_units():
    result = validate_net_contents("0.75 L", 750)

    assert result["status"] == "PASS"


def test_net_contents_fail():
    result = validate_net_contents("1 L", 750)

    assert result["status"] == "FAIL"


def test_valid_government_warning_passes():
    result = validate_warning(VALID_WARNING)

    assert result["status"] == "PASS"


def test_incomplete_government_warning_fails():
    result = validate_warning(
        "GOVERNMENT WARNING: Alcohol may cause health problems."
    )

    assert result["status"] == "FAIL"


def test_missing_government_warning_fails():
    result = validate_warning("OLD TOM DISTILLERY 45% ALC./VOL.")

    assert result["status"] == "FAIL"


def test_overall_pass():
    fields = {
        "brand": {"status": "PASS"},
        "abv": {"status": "PASS"},
        "warning": {"status": "PASS"},
    }

    assert determine_overall_status(fields) == "PASS"


def test_overall_fail_takes_priority():
    fields = {
        "brand": {"status": "PASS"},
        "abv": {"status": "FAIL"},
        "warning": {"status": "REVIEW"},
    }

    assert determine_overall_status(fields) == "FAIL"


def test_overall_review():
    fields = {
        "brand": {"status": "PASS"},
        "abv": {"status": "REVIEW"},
        "warning": {"status": "PASS"},
    }

    assert determine_overall_status(fields) == "REVIEW"


def test_low_confidence_brand_goes_to_review():
    ocr_lines = [
        {
            "text": "OLD TOM DISTILLERY",
            "confidence": 0.70,
            "low_confidence": True,
        }
    ]

    result = validate_text_field(
        "OLD TOM DISTILLERY",
        "OLD TOM DISTILLERY",
        ocr_lines,
    )

    assert result["status"] == "REVIEW"


def test_low_confidence_abv_goes_to_review():
    ocr_lines = [
        {
            "text": "45% Alc./Vol.",
            "confidence": 0.70,
            "low_confidence": True,
        }
    ]

    result = validate_abv(
        "45%",
        45.0,
        ocr_lines,
    )

    assert result["status"] == "REVIEW"


def test_low_confidence_net_contents_goes_to_review():
    ocr_lines = [
        {
            "text": "750 mL",
            "confidence": 0.70,
            "low_confidence": True,
        }
    ]

    result = validate_net_contents(
        "750 mL",
        750,
        ocr_lines,
    )

    assert result["status"] == "REVIEW"


def test_low_confidence_warning_goes_to_review():
    ocr_lines = [
        {
            "text": (
                "GOVERNMENT WARNING: "
                "(1) According to the Surgeon General, women should not drink "
                "alcoholic beverages during pregnancy because of the risk of "
                "birth defects."
            ),
            "confidence": 0.70,
            "low_confidence": True,
        },
        {
            "text": (
                "(2) Consumption of alcoholic beverages impairs "
                "your ability to drive a car or operate machinery, "
                "and may cause health problems."
            ),
            "confidence": 0.99,
            "low_confidence": False,
        },
    ]

    ocr_text = " ".join(line["text"] for line in ocr_lines)

    result = validate_warning(
        ocr_text,
        ocr_lines,
    )

    assert result["status"] == "REVIEW"


def test_overall_review_when_one_field_has_low_confidence():
    fields = {
        "brand_name": {"status": "PASS"},
        "class_type": {"status": "PASS"},
        "alcohol_content": {"status": "REVIEW"},
        "net_contents": {"status": "PASS"},
        "government_warning": {"status": "PASS"},
    }

    assert determine_overall_status(fields) == "REVIEW"

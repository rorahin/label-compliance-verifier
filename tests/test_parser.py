from app.parser import (
    normalize_text,
    extract_abv,
    extract_net_contents,
    detect_government_warning,
    extract_government_warning,
)


def test_normalize_text():
    result = normalize_text("  Old   Tom Distillery  ")
    assert result == "OLD TOM DISTILLERY"


def test_extract_abv_integer():
    assert extract_abv("45% Alc./Vol.") == 45.0


def test_extract_abv_decimal():
    assert extract_abv("12.5 % ABV") == 12.5


def test_extract_abv_missing():
    assert extract_abv("Alcohol content unavailable") is None


def test_extract_net_contents_ml():
    assert extract_net_contents("750 mL") == 750


def test_extract_net_contents_liters():
    assert extract_net_contents("0.75 L") == 750


def test_extract_net_contents_one_liter():
    assert extract_net_contents("1 L") == 1000


def test_government_warning_found():
    text = "GOVERNMENT WARNING: Example warning."
    assert detect_government_warning(text) is True


def test_government_warning_missing():
    text = "OLD TOM DISTILLERY 45% ALC./VOL."
    assert detect_government_warning(text) is False


def test_extract_government_warning():
    text = (
        "OLD TOM DISTILLERY "
        "GOVERNMENT WARNING: Example warning."
    )

    assert extract_government_warning(text) == (
        "GOVERNMENT WARNING: EXAMPLE WARNING."
    )

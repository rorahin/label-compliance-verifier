import re


def normalize_text(text: str) -> str:
    """
    Normalize text so OCR and application values
    can be compared more reliably.
    """
    text = text.upper()
    text = text.replace("’", "'")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_abv(text: str):
    """
    Extract alcohol percentage from OCR text.

    Examples:
    45% -> 45.0
    45 % ABV -> 45.0
    12.5% Alc./Vol. -> 12.5
    """
    text = normalize_text(text)

    match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)

    if not match:
        return None

    return float(match.group(1))


def extract_net_contents(text: str):
    """
    Extract net contents and normalize to milliliters.

    Examples:
    750 mL -> 750
    0.75 L -> 750
    1 L -> 1000
    """
    text = normalize_text(text)

    match = re.search(r"(\d+(?:\.\d+)?)\s*(ML|L)\b", text)

    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2)

    if unit == "L":
        value *= 1000

    if value.is_integer():
        return int(value)

    return value


def extract_government_warning(text: str):
    """
    Return the Government Warning portion of the OCR text.
    """
    normalized = normalize_text(text)

    heading = "GOVERNMENT WARNING:"
    position = normalized.find(heading)

    if position == -1:
        return None

    return normalized[position:]


def detect_government_warning(text: str) -> bool:
    """
    Return True when a Government Warning heading is present.
    """
    return extract_government_warning(text) is not None


if __name__ == "__main__":
    sample = """
    OLD TOM DISTILLERY
    Kentucky Straight Bourbon Whiskey
    45% Alc./Vol. (90 Proof)
    750 mL
    GOVERNMENT WARNING:
    Alcohol may cause health problems.
    """

    print("Normalized:")
    print(normalize_text(sample))

    print("\nABV:")
    print(extract_abv(sample))

    print("\nNet Contents:")
    print(extract_net_contents(sample))

    print("\nGovernment Warning Found:")
    print(detect_government_warning(sample))

    print("\nExtracted Government Warning:")
    print(extract_government_warning(sample))

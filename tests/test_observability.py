from uuid import UUID

from app.observability import (
    get_request_id,
)


def test_valid_request_id_is_preserved():
    request_id = "treasury-test-123"

    assert get_request_id(request_id) == request_id


def test_missing_request_id_generates_uuid():
    request_id = get_request_id()

    parsed = UUID(request_id)

    assert str(parsed) == request_id


def test_malicious_request_id_is_rejected():
    malicious = "safe-id\nFAKE-LOG: attacker"

    result = get_request_id(malicious)

    assert result != malicious

    UUID(result)


def test_overly_long_request_id_is_rejected():
    supplied = "a" * 1000

    result = get_request_id(supplied)

    assert result != supplied

    UUID(result)

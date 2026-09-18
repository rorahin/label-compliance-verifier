from starlette.responses import Response

from app.security_headers import apply_security_headers


def test_security_headers_are_applied():
    response = Response()

    apply_security_headers(response)

    assert response.headers["X-Content-Type-Options"] == "nosniff"

    assert response.headers["X-Frame-Options"] == "DENY"

    assert (
        response.headers["Referrer-Policy"]
        == "strict-origin-when-cross-origin"
    )

    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"

    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"


def test_content_security_policy_is_restrictive():
    response = Response()

    apply_security_headers(response)

    csp = response.headers["Content-Security-Policy"]

    assert "default-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "form-action 'self'" in csp


def test_sensitive_browser_permissions_are_disabled():
    response = Response()

    apply_security_headers(response)

    policy = response.headers["Permissions-Policy"]

    assert "camera=()" in policy
    assert "microphone=()" in policy
    assert "geolocation=()" in policy

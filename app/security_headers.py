from starlette.responses import Response

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data: blob:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "frame-ancestors 'none'; "
    "form-action 'self'"
)


def apply_security_headers(response: Response) -> Response:
    """
    Apply browser security headers to application responses.
    """
    response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY

    response.headers["X-Content-Type-Options"] = "nosniff"

    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    response.headers["X-Frame-Options"] = "DENY"

    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )

    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

    return response

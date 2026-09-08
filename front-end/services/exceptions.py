"""Exceptions raised by the services layer (services/*).

Views should catch these instead of httpx exceptions directly, so the
transport library used to talk to the FastAPI backend stays an implementation
detail hidden behind services/api_client.py.

Mapped from the backend's error format (see ../API_CONTRACT.md#error-format):
401 auth, 403 role, 404 not found/not yours, 409 conflict (duplicate,
insufficient stock, invalid status transition), 422 validation.
"""


class ApiError(Exception):
    """Base class for all errors raised by the API client."""

    def __init__(self, message: str, status_code: int | None = None, payload: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}

    @property
    def detail(self) -> str:
        """Human-readable detail from the backend's {"detail": ...} body,
        falling back to the exception message.

        On 422s `detail` is a list of Pydantic field errors (`{"loc": [...],
        "msg": ...}`), not a string -- join those into one readable message.
        """
        detail = self.payload.get("detail")
        if isinstance(detail, str):
            return detail
        if isinstance(detail, list):
            messages = [item.get("msg", "") for item in detail if isinstance(item, dict)]
            if messages:
                return "; ".join(messages)
        return self.message


class ApiConnectionError(ApiError):
    """Raised when the backend API could not be reached at all."""


class ApiTimeoutError(ApiError):
    """Raised when the backend API did not respond in time."""


class ApiResponseError(ApiError):
    """Raised when the backend API responded with an HTTP error status."""


class ApiNotFoundError(ApiResponseError):
    """Raised for HTTP 404 responses (not found, or not the caller's)."""


class ApiAuthenticationError(ApiResponseError):
    """Raised for HTTP 401 responses (missing/invalid/expired token)."""


class ApiPermissionError(ApiResponseError):
    """Raised for HTTP 403 responses (role not permitted)."""


class ApiConflictError(ApiResponseError):
    """Raised for HTTP 409 responses (duplicate field, out of stock,
    invalid order-status transition)."""


class ApiValidationError(ApiResponseError):
    """Raised for HTTP 422 responses (request body failed validation)."""

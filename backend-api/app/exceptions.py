"""Domain-level exceptions, decoupled from HTTP. Routers/main.py translate
these into proper HTTP responses via the registered exception handlers."""


class AppError(Exception):
    """Base class for all domain errors."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class NotFoundError(AppError):
    """Requested resource does not exist."""


class ConflictError(AppError):
    """Request conflicts with current state (e.g. duplicate unique field)."""


class ValidationAppError(AppError):
    """Semantic validation failure not expressible via Pydantic alone."""


class InsufficientStockError(AppError):
    """Not enough inventory available to satisfy a reservation."""


class AuthenticationError(AppError):
    """Invalid credentials or token."""


class AuthorizationError(AppError):
    """Authenticated but not allowed to perform this action."""


class InvalidStateTransitionError(AppError):
    """Attempted an invalid lifecycle transition (order/payment/shipment)."""

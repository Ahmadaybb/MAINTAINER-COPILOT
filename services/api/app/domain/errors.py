from __future__ import annotations

from typing import Any


class DomainError(Exception):
    def __init__(self, message: str, code: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class NotFoundError(DomainError):
    def __init__(self, message: str = "The requested resource was not found.") -> None:
        super().__init__(message=message, code="not_found")


class PermissionDenied(DomainError):
    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(message=message, code="permission_denied")


class ToolFailure(DomainError):
    def __init__(self, message: str = "A tool failed but the conversation can continue.") -> None:
        super().__init__(message=message, code="tool_failure")


class RateLimited(DomainError):
    def __init__(self, message: str = "Please try again shortly.") -> None:
        super().__init__(message=message, code="rate_limited")


class UpstreamUnavailable(DomainError):
    def __init__(self, message: str = "An upstream service is temporarily unavailable.") -> None:
        super().__init__(message=message, code="upstream_unavailable")


class ValidationError(DomainError):
    def __init__(self, message: str = "The request is invalid.") -> None:
        super().__init__(message=message, code="validation_error")


class BootValidationError(DomainError):
    def __init__(self, message: str = "The service failed startup validation.") -> None:
        super().__init__(message=message, code="boot_validation_error")

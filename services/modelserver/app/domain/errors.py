from __future__ import annotations


class BootValidationError(Exception):
    def __init__(self, message: str = "The modelserver failed startup validation.") -> None:
        super().__init__(message)
        self.message = message
        self.code = "boot_validation_error"

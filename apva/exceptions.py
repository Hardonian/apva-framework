"""APVA exception hierarchy.

A structured exception tree lets callers catch at the right granularity:

* ``APVAError``  — catch-all for any APVA-originated error.
* ``APVAValidationError``  — invalid inputs to models or calculators.
* ``APVACalculationError`` — numerical failures during TVY computation.
* ``APVAConfigurationError`` — missing / malformed configuration.
* ``APVANetworkError``  — HTTP / connectivity failures (SDK, proxy).
* ``APVARateLimitError``  — client exceeded rate limits.
* ``APVAAuthenticationError`` — invalid or missing credentials.
"""

from __future__ import annotations


class APVAError(Exception):
    """Base exception for all APVA framework errors."""


class APVAValidationError(APVAError):
    """Raised when input data fails Pydantic or business-rule validation."""


class APVACalculationError(APVAError):
    """Raised when the TVY engine encounters an unrecoverable numerical error."""


class APVAConfigurationError(APVAError):
    """Raised when required configuration is missing or malformed."""


class APVANetworkError(APVAError):
    """Raised when an HTTP call to the backend or target fails."""


class APVARateLimitError(APVAError):
    """Raised when the client has exceeded the allowed request rate."""


class APVAAuthenticationError(APVAError):
    """Raised when API key validation or SSO authentication fails."""

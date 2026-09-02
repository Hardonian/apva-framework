"""Unit tests for the apva.exceptions module."""

from __future__ import annotations

import pytest

from apva.exceptions import (
    APVAAuthenticationError,
    APVACalculationError,
    APVAConfigurationError,
    APVAError,
    APVANetworkError,
    APVARateLimitError,
    APVAValidationError,
)


def test_exception_inheritance():
    assert issubclass(APVAValidationError, APVAError)
    assert issubclass(APVACalculationError, APVAError)
    assert issubclass(APVAConfigurationError, APVAError)
    assert issubclass(APVANetworkError, APVAError)
    assert issubclass(APVARateLimitError, APVAError)
    assert issubclass(APVAAuthenticationError, APVAError)


def test_raise_and_catch():
    with pytest.raises(APVAError):
        raise APVAValidationError("Invalid parameter")

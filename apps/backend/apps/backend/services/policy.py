"""Enterprise Safeguard Circuit Breaker Policy Engine."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Global in-memory storage for tenant safeguard policies
_tenant_policies: dict[int, dict[str, Any]] = {}


class SafeguardCircuitBreaker:
    """Evaluates telemetry and requests against dynamic enterprise safeguard policies."""

    def __init__(self, tenant_id: int) -> None:
        self.tenant_id = tenant_id
        policy = _tenant_policies.get(tenant_id, {})
        self.max_guardrail_tax_min = float(policy.get("max_guardrail_tax_min", 2.0))
        self.pii_redaction_enabled = bool(policy.get("pii_redaction_enabled", True))
        self.strict_mode = bool(policy.get("strict_mode", False))

    @classmethod
    def get_policy(cls, tenant_id: int) -> dict[str, Any]:
        """Retrieve policy configuration for a tenant."""
        return _tenant_policies.get(
            tenant_id,
            {
                "max_guardrail_tax_min": 2.0,
                "pii_redaction_enabled": True,
                "strict_mode": False,
            },
        )

    @classmethod
    def set_policy(cls, tenant_id: int, policy: dict[str, Any]) -> dict[str, Any]:
        """Update policy configuration for a tenant."""
        _tenant_policies[tenant_id] = {
            "max_guardrail_tax_min": float(policy.get("max_guardrail_tax_min", 2.0)),
            "pii_redaction_enabled": bool(policy.get("pii_redaction_enabled", True)),
            "strict_mode": bool(policy.get("strict_mode", False)),
        }
        return _tenant_policies[tenant_id]

    def validate_guardrail_latency(self, latency_min: float) -> bool:
        """Check if guardrail tax exceeds the maximum allowable latency."""
        if latency_min > self.max_guardrail_tax_min:
            logger.warning(
                "CIRCUIT BREAKER: Guardrail latency %.4f exceeds max %.4f for tenant %d",
                latency_min,
                self.max_guardrail_tax_min,
                self.tenant_id,
            )
            return False
        return True

    def redact_pii(self, text: str) -> str:
        """Apply PII redaction rules if enabled by policy."""
        if not self.pii_redaction_enabled or not text:
            return text

        # Strip emails
        redacted = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[REDACTED_EMAIL]", text)
        # Strip SSNs
        redacted = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", redacted)
        # Strip credit card numbers (13-16 digits with optional dashes/spaces)
        redacted = re.sub(r"\b(?:\d[ -]*?){13,16}\b", "[REDACTED_CARD]", redacted)
        # Strip phone numbers
        redacted = re.sub(
            r"\b(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b", "[REDACTED_PHONE]", redacted
        )
        return redacted

    def sanitize_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Recursively redact PII from structured metadata dictionaries."""
        if not self.pii_redaction_enabled or not metadata:
            return metadata

        sanitized: dict[str, Any] = {}
        for k, v in metadata.items():
            if isinstance(v, str):
                sanitized[k] = self.redact_pii(v)
            elif isinstance(v, dict):
                sanitized[k] = self.sanitize_metadata(v)
            elif isinstance(v, list):
                sanitized[k] = [
                    self.redact_pii(item) if isinstance(item, str) else item for item in v
                ]
            else:
                sanitized[k] = v
        return sanitized

"""Workflow client for APVA enterprise business-case and portfolio gates."""

from __future__ import annotations

import os
import uuid
from typing import Any, Iterable, Mapping

import httpx


class APVAWorkflowGateError(RuntimeError):
    """Raised when an analyzed use case does not meet an allowed rollout posture."""

    def __init__(self, report: Mapping[str, Any], allowed: Iterable[str]) -> None:
        self.report = dict(report)
        self.allowed = tuple(allowed)
        decision = self.report.get("decision", "unknown")
        failed = [
            check.get("label", check.get("check", "unknown"))
            for check in self.report.get("gate_checks", [])
            if not check.get("passed", False)
        ]
        details = f"; failed gates: {', '.join(failed)}" if failed else ""
        super().__init__(
            f"APVA workflow gate rejected decision '{decision}'; "
            f"allowed: {', '.join(self.allowed)}{details}"
        )


class APVAEnterpriseClient:
    """Persistent HTTP client for enterprise analysis and policy gates."""

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        base_url = api_url or os.getenv("APVA_API_URL", "http://localhost:8000/api/v1")
        headers = {"Accept": "application/json", "User-Agent": "apva-sdk/3.0"}
        resolved_api_key = api_key or os.getenv("APVA_API_KEY")
        if resolved_api_key:
            headers["Authorization"] = f"Bearer {resolved_api_key}"
        self._client = httpx.Client(
            base_url=base_url.rstrip("/") + "/",
            headers=headers,
            timeout=timeout,
            transport=transport,
        )

    def analyze_business_case(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Generate an enterprise business case from a validated request payload."""
        return self._post("analysis/business-case", payload)

    def analyze_portfolio(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Rank a portfolio and allocate its optional investment budget."""
        return self._post("analysis/portfolio", payload)

    def policy_template(self) -> dict[str, Any]:
        """Fetch the server's transparent default governance policy."""
        response = self._client.get(
            "analysis/policy-template",
            headers={"X-Request-ID": uuid.uuid4().hex},
        )
        response.raise_for_status()
        return dict(response.json())

    def require_decision(
        self,
        report: Mapping[str, Any],
        allowed: Iterable[str] = ("scale",),
    ) -> Mapping[str, Any]:
        """Fail a deployment or CI workflow unless the decision is allowed."""
        allowed_decisions = tuple(allowed)
        if report.get("decision") not in allowed_decisions:
            raise APVAWorkflowGateError(report, allowed_decisions)
        return report

    def analyze_and_gate(
        self,
        payload: Mapping[str, Any],
        allowed: Iterable[str] = ("scale",),
    ) -> dict[str, Any]:
        """Analyze a use case and raise immediately when its policy gates fail."""
        report = self.analyze_business_case(payload)
        self.require_decision(report, allowed)
        return report

    def _post(self, path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        response = self._client.post(
            path,
            json=dict(payload),
            headers={"X-Request-ID": uuid.uuid4().hex},
        )
        response.raise_for_status()
        return dict(response.json())

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> APVAEnterpriseClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

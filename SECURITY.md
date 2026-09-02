# APVA Security & Compliance Specification

## 1. Security Architecture & Threat Model

The **APVA (AI Productivity & Value Architecture)** framework processes high-throughput operational and agentic telemetry across distributed systems. APVA is engineered following **Defense-in-Depth**, **Zero-Trust**, and **Least-Privilege** principles.

### Key Architectural Safeguards

- **Zero Plaintext Storage**: Client API keys are never stored in plaintext. Ingestion endpoints compute a salted `SHA-256` hex digest immediately upon receipt and match against indexed hashes in the `tenants` table.
- **Edge PII Redaction**: Telemetry ingesting workers redact sensitive information (emails, Social Security numbers, third-party provider keys such as `sk-`, `ghp_`, and `apva_`) before buffering or persistence.
- **Circuit-Broken Ingestion**: In the event of secondary sink outages (ClickHouse, Stripe, Redis), the transactional OLTP database remains isolated and operational. Secondary failures do not compromise core execution.
- **Memory-Safe Rate Limiting**: In-memory rate limiting employs deterministic bucket eviction on expired 60-second windows, preventing Denial-of-Service attacks via state bloat.

---

## 2. API Authentication & Key Lifecycle

APVA enforces strict token-based authorization via HTTP Bearer headers:

```http
Authorization: Bearer apva_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Key Rotation Procedure

Organizations can rotate credentials zero-downtime using the Tenants API:

```bash
curl -X POST https://api.apva.io/api/v1/tenants/rotate-key \
  -H "Authorization: Bearer <CURRENT_API_KEY>"
```

Upon execution:

1. A cryptographically secure 256-bit entropy key is generated (`secrets.token_urlsafe(32)`).
2. The SHA-256 hash is committed to the database.
3. The raw key is returned in the response body **exactly once**.
4. The previous key is invalidated immediately.

---

## 3. Network & Infrastructure Security

- **Network Isolation**: Backend databases (PostgreSQL, ClickHouse, Redis) are isolated on private container networks (`apva-internal-network`) with no public ingress.
- **Transport Security**: All HTTP communication enforces TLS 1.3 with Strict-Transport-Security (`HSTS` max-age=63072000, preload).
- **Security Headers**: All API responses include `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and strict `Content-Security-Policy`.

---

## 4. Responsible Vulnerability Disclosure

If you discover a potential vulnerability in APVA or related Hardonia services, please notify our security team responsibly.

**Do NOT file public issues or pull requests detailing undisclosed vulnerabilities.**

### Contact Information

- **Security Email**: [security@hardonia.store](mailto:security@hardonia.store)
- **PGP Key**: Available upon request.
- **Expected Acknowledgment**: Within 24–48 hours.
- **Remediation & Patch Target**: Within 7 business days.

Please provide:

- A clear explanation of the potential vulnerability.
- Proof-of-concept steps or payload examples.
- Potential impact on tenant data or service availability.

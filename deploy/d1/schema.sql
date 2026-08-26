-- APVA D1 Edge Schema for Multi-Tenant Telemetry and Edge Buffering

CREATE TABLE IF NOT EXISTS tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    api_key_hash TEXT NOT NULL UNIQUE,
    stripe_customer_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS telemetry_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    app_name TEXT NOT NULL,
    session_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    human_baseline_time REAL NOT NULL,
    ai_augmented_time REAL NOT NULL,
    guardrail_latency_tax REAL NOT NULL,
    session_iterations INTEGER DEFAULT 1,
    hourly_rate_usd REAL,
    is_shadow INTEGER DEFAULT 0,
    metadata_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evaluation_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    transcript_id TEXT NOT NULL,
    query TEXT NOT NULL,
    context TEXT NOT NULL,
    answer TEXT NOT NULL,
    expected_answer TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    exact_span_recall REAL,
    llm_faithfulness_score REAL,
    precision_score REAL,
    rag_reliability_coefficient REAL,
    error_message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS audits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_name TEXT NOT NULL,
    repo_url TEXT,
    audited_at TEXT NOT NULL,
    overall_score REAL,
    critical_findings INTEGER DEFAULT 0,
    high_findings INTEGER DEFAULT 0,
    medium_findings INTEGER DEFAULT 0,
    total_findings INTEGER DEFAULT 0,
    report_json TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    recommendation TEXT,
    resource_type TEXT,
    resource_name TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_id INTEGER NOT NULL,
    format TEXT DEFAULT 'markdown',
    content TEXT,
    delivered_via TEXT,
    delivered_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_telemetry_tenant ON telemetry_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_app ON telemetry_events(app_name);
CREATE INDEX IF NOT EXISTS idx_telemetry_session ON telemetry_events(session_id);
CREATE INDEX IF NOT EXISTS idx_eval_tenant ON evaluation_jobs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_eval_status ON evaluation_jobs(status);
CREATE INDEX IF NOT EXISTS idx_audit_workspace ON audits(workspace_name);
CREATE INDEX IF NOT EXISTS idx_audit_status ON audits(status);
CREATE INDEX IF NOT EXISTS idx_finding_audit ON findings(audit_id);
CREATE INDEX IF NOT EXISTS idx_finding_severity ON findings(severity);
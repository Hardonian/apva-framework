import { useEffect, useState } from 'react';
import axios from 'axios';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import './App.css';

const API_BASE = import.meta.env.VITE_API_URL || '';

interface MetricsData {
  telemetry_count: number;
  evaluation_count: number;
  avg_gross_time_saved_min: number;
  avg_guardrail_tax_min: number;
  avg_rag_reliability_coefficient: number;
  macro_tvy_min: number;
  avg_true_value_yield_usd: number | null;
  total_tvy_min: number;
  total_tvy_usd: number | null;
  value_per_1000_events_usd: number | null;
  shadow_event_count: number;
  shadow_event_rate: number;
  hourly_rate_coverage: number;
  is_net_positive: boolean;
}

interface Insight {
  severity: 'info' | 'high' | 'critical';
  metric: string;
  observation: string;
  prescription: string;
  estimated_savings_usd_per_10k: number;
  sample_size: number;
  confidence: number;
}

interface BenchmarksData {
  global_percentiles: {
    rag_reliability: {
      your_percentile: number;
      p50: number;
      p90: number;
      p99: number;
      message: string;
    };
    guardrail_tax_ms: {
      your_percentile: number;
      p50: number;
      p90: number;
      p99: number;
      message: string;
    };
  };
}

interface TimeseriesPoint {
  name: string;
  date: string;
  tvy: number;
  tvyUsd: number;
  sample_count: number;
  efficiency_percent: number;
  data_source: 'observed' | 'no_data';
}

interface TenantProfile {
  id: number;
  name: string;
  tier: string;
  created_at: string;
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    return Boolean(localStorage.getItem('apva_token'));
  });
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [benchmarks, setBenchmarks] = useState<BenchmarksData | null>(null);
  const [timeseries, setTimeseries] = useState<TimeseriesPoint[]>([]);
  const [tenantProfile, setTenantProfile] = useState<TenantProfile | null>(null);
  const [workspaces, setWorkspaces] = useState<{ id: number; name: string; role: string; key: string; status: string }[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Login form state
  const [authMode, setAuthMode] = useState<'sso' | 'apikey'>('sso');
  const [email, setEmail] = useState<string>('');
  const [apiKeyInput, setApiKeyInput] = useState<string>('');
  const [loginError, setLoginError] = useState<string | null>(null);

  // Navigation tab
  const [activeTab, setActiveTab] = useState<'overview' | 'safeguards' | 'workspaces'>('overview');

  // Safeguards state
  const [maxTax, setMaxTax] = useState<number>(2.0);
  const [piiEnabled, setPiiEnabled] = useState<boolean>(true);
  const [strictMode, setStrictMode] = useState<boolean>(false);
  const [policyMessage, setPolicyMessage] = useState<string | null>(null);
  const [savingPolicy, setSavingPolicy] = useState<boolean>(false);

  // Workspaces provision modal state
  const [showModal, setShowModal] = useState<boolean>(false);
  const [newOrgName, setNewOrgName] = useState<string>('');
  const [newOrgTier, setNewOrgTier] = useState<string>('team');
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [provisioning, setProvisioning] = useState<boolean>(false);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('apva_token') || 'dev-local-key';
    return { Authorization: `Bearer ${token}` };
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError(null);

    if (authMode === 'apikey') {
      if (!apiKeyInput.trim()) {
        setLoginError('Please enter an API Key');
        return;
      }
      localStorage.setItem('apva_token', apiKeyInput.trim());
      setIsAuthenticated(true);
      return;
    }

    try {
      const res = await axios.post(`${API_BASE}/api/v1/auth/sso/login`, {
        email: email,
        connection: 'saml-okta',
      });
      if (res.data.access_token) {
        localStorage.setItem('apva_token', res.data.access_token);
        setIsAuthenticated(true);
      }
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setLoginError(err.response?.data?.detail || 'SSO Authentication Failed');
      } else {
        setLoginError('An unexpected error occurred during login');
      }
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('apva_token');
    setIsAuthenticated(false);
    setMetrics(null);
    setInsights([]);
    setBenchmarks(null);
  };

  // Fetch all live dashboard data
  useEffect(() => {
    if (!isAuthenticated) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const headers = getAuthHeaders();

        const [metricsRes, insightsRes, benchmarksRes, timeseriesRes, tenantRes, safeguardRes] = await Promise.all([
          axios.get(`${API_BASE}/api/v1/metrics/tvy`, { headers }),
          axios.get(`${API_BASE}/api/v1/metrics/insights`, { headers }),
          axios.get(`${API_BASE}/api/v1/metrics/benchmarks`, { headers }),
          axios.get(`${API_BASE}/api/v1/metrics/timeseries?days=5`, { headers }),
          axios.get(`${API_BASE}/api/v1/tenants/me`, { headers }),
          axios.get(`${API_BASE}/api/v1/safeguards`, { headers }),
        ]);

        setMetrics(metricsRes.data);
        setInsights(insightsRes.data);
        setBenchmarks(benchmarksRes.data);
        setTimeseries(timeseriesRes.data);

        const prof = tenantRes.data;
        setTenantProfile(prof);
        setWorkspaces([
          {
            id: prof.id,
            name: prof.name,
            role: 'Admin',
            key: 'pk_live_...' + prof.id,
            status: 'Active',
          },
        ]);

        if (safeguardRes.data) {
          setMaxTax(safeguardRes.data.max_guardrail_tax_min ?? 2.0);
          setPiiEnabled(safeguardRes.data.pii_redaction_enabled ?? true);
          setStrictMode(safeguardRes.data.strict_mode ?? false);
        }

        setLoading(false);
      } catch (err: unknown) {
        if (axios.isAxiosError(err) && err.response?.status === 401) {
          handleLogout();
          setError('Session expired or invalid credentials. Please log in again.');
        } else if (err instanceof Error) {
          setError(err.message || 'Failed to fetch telemetry metrics');
        } else {
          setError('An unknown communication error occurred');
        }
        setLoading(false);
      }
    };

    fetchData();
  }, [isAuthenticated]);

  const handleSavePolicy = async () => {
    setSavingPolicy(true);
    setPolicyMessage(null);
    try {
      const headers = getAuthHeaders();
      await axios.put(
        `${API_BASE}/api/v1/safeguards`,
        {
          max_guardrail_tax_min: maxTax,
          pii_redaction_enabled: piiEnabled,
          strict_mode: strictMode,
        },
        { headers }
      );
      setPolicyMessage('Safeguard policies successfully persisted.');
      setTimeout(() => setPolicyMessage(null), 4000);
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setPolicyMessage(`Failed to update policy: ${err.response?.data?.detail || err.message}`);
      } else {
        setPolicyMessage('Failed to update safeguard policy.');
      }
    } finally {
      setSavingPolicy(false);
    }
  };

  const handleProvisionWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newOrgName.trim()) return;
    setProvisioning(true);
    try {
      const headers = getAuthHeaders();
      const res = await axios.post(
        `${API_BASE}/api/v1/tenants`,
        {
          name: newOrgName.trim(),
          tier: newOrgTier,
        },
        { headers }
      );
      setCreatedKey(res.data.api_key);
      setWorkspaces((prev) => [
        ...prev,
        {
          id: res.data.id,
          name: res.data.name,
          role: 'Admin',
          key: res.data.api_key.slice(0, 10) + '...',
          status: 'Active',
        },
      ]);
      setNewOrgName('');
    } catch {
      alert('Failed to provision workspace.');
    } finally {
      setProvisioning(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="login-container">
        <div className="login-card">
          <h1>APVA Analytical Engine</h1>
          <p>Enterprise AI Productivity & Value Architecture</p>

          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', justifyContent: 'center' }}>
            <button
              type="button"
              style={{
                padding: '0.4rem 0.8rem',
                background: authMode === 'sso' ? '#6c5ce7' : '#2a2a2a',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
              onClick={() => setAuthMode('sso')}
            >
              SSO / SAML
            </button>
            <button
              type="button"
              style={{
                padding: '0.4rem 0.8rem',
                background: authMode === 'apikey' ? '#6c5ce7' : '#2a2a2a',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
              onClick={() => setAuthMode('apikey')}
            >
              API Key
            </button>
          </div>

          <form onSubmit={handleLogin} className="login-form">
            {authMode === 'sso' ? (
              <input
                type="email"
                placeholder="name@acmecorp.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            ) : (
              <input
                type="password"
                placeholder="apva_live_..."
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                required
              />
            )}
            {loginError && <div className="login-error">{loginError}</div>}
            <button type="submit">
              {authMode === 'sso' ? 'Continue with SSO' : 'Authenticate with API Key'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  if (loading) return <div className="loader">Initializing APVA Analytical Engine...</div>;
  if (error) return <div className="error">Metrics resolution failure: {error}</div>;

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="tenant-badge">
            Organization: {tenantProfile?.name || 'Default Organization'} ({tenantProfile?.tier || 'Community'})
          </div>
          <button
            onClick={handleLogout}
            style={{
              padding: '0.35rem 0.85rem',
              background: '#2a2a2a',
              color: '#bbb',
              border: '1px solid #444',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Sign Out
          </button>
        </div>
        <h1>APVA True Value Yield Dashboard</h1>
        <p>Enterprise Inference Analytics & Operational Directives</p>
        <div className="tabs" style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
          <button
            style={{
              padding: '0.5rem 1rem',
              background: activeTab === 'overview' ? '#6c5ce7' : '#2a2a2a',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
            onClick={() => setActiveTab('overview')}
          >
            Overview
          </button>
          <button
            style={{
              padding: '0.5rem 1rem',
              background: activeTab === 'safeguards' ? '#6c5ce7' : '#2a2a2a',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
            onClick={() => setActiveTab('safeguards')}
          >
            Safeguard Policies
          </button>
          <button
            style={{
              padding: '0.5rem 1rem',
              background: activeTab === 'workspaces' ? '#6c5ce7' : '#2a2a2a',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
            onClick={() => setActiveTab('workspaces')}
          >
            Workspaces
          </button>
        </div>
      </header>

      {activeTab === 'overview' && (
        <div className="layout-grid">
          <div className="main-content">
            <div className="metrics-grid">
              <div className={`metric-card ${metrics?.is_net_positive ? 'positive' : 'negative'}`}>
                <h3>Macro TVY (Minutes)</h3>
                <div className="metric-value">{metrics?.macro_tvy_min.toFixed(2)}m</div>
              </div>
              <div className={`metric-card ${metrics?.is_net_positive ? 'positive' : 'negative'}`}>
                <h3>Financial TVY (USD)</h3>
                <div className="metric-value">${metrics?.avg_true_value_yield_usd?.toFixed(2) || '0.00'}</div>
              </div>
              <div className="metric-card">
                <h3>Avg Guardrail Tax</h3>
                <div className="metric-value">{metrics?.avg_guardrail_tax_min.toFixed(2)}m</div>
              </div>
              <div className="metric-card">
                <h3>RAG Reliability</h3>
                <div className="metric-value">
                  {((metrics?.avg_rag_reliability_coefficient ?? 0) * 100).toFixed(1)}%
                </div>
              </div>
              <div className={`metric-card ${metrics?.is_net_positive ? 'positive' : 'negative'}`}>
                <h3>Total Value Captured</h3>
                <div className="metric-value">${metrics?.total_tvy_usd?.toFixed(2) || '0.00'}</div>
              </div>
              <div className="metric-card">
                <h3>Observed Runs</h3>
                <div className="metric-value">{metrics?.telemetry_count.toLocaleString() || '0'}</div>
              </div>
              <div className="metric-card">
                <h3>Financial Coverage</h3>
                <div className="metric-value">{((metrics?.hourly_rate_coverage ?? 0) * 100).toFixed(1)}%</div>
              </div>
              <div className="metric-card">
                <h3>Shadow Event Rate</h3>
                <div className="metric-value">{((metrics?.shadow_event_rate ?? 0) * 100).toFixed(1)}%</div>
              </div>
            </div>

            <div className="chart-container">
              <h2>TVY Trending (Last 5 Days)</h2>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={timeseries}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis dataKey="name" stroke="#ccc" />
                  <YAxis stroke="#ccc" />
                  <Tooltip contentStyle={{ backgroundColor: '#1e1e1e', borderColor: '#333' }} />
                  <Legend />
                  <Line type="monotone" dataKey="tvy" stroke="#8884d8" name="TVY (Minutes)" strokeWidth={3} />
                  <Line type="monotone" dataKey="tvyUsd" stroke="#82ca9d" name="TVY (USD)" strokeWidth={3} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="sidebar">
            <div className="benchmarks-panel" style={{ marginBottom: '2rem' }}>
              <h2>Global Network Percentiles</h2>
              {benchmarks && (
                <div className="benchmark-cards">
                  <div
                    className="benchmark-card"
                    style={{ padding: '1rem', background: '#252526', borderRadius: '8px', marginBottom: '1rem' }}
                  >
                    <h4 style={{ margin: '0 0 0.5rem 0' }}>
                      RAG Reliability (p{benchmarks.global_percentiles.rag_reliability.your_percentile})
                    </h4>
                    <div style={{ height: '8px', background: '#333', borderRadius: '4px', marginBottom: '0.5rem' }}>
                      <div
                        style={{
                          height: '100%',
                          background: '#82ca9d',
                          borderRadius: '4px',
                          width: `${benchmarks.global_percentiles.rag_reliability.your_percentile}%`,
                        }}
                      ></div>
                    </div>
                    <p style={{ fontSize: '0.85rem', color: '#ccc', margin: 0 }}>
                      {benchmarks.global_percentiles.rag_reliability.message}
                    </p>
                  </div>
                  <div
                    className="benchmark-card"
                    style={{ padding: '1rem', background: '#252526', borderRadius: '8px' }}
                  >
                    <h4 style={{ margin: '0 0 0.5rem 0' }}>
                      Guardrail Tax (p{benchmarks.global_percentiles.guardrail_tax_ms.your_percentile})
                    </h4>
                    <div style={{ height: '8px', background: '#333', borderRadius: '4px', marginBottom: '0.5rem' }}>
                      <div
                        style={{
                          height: '100%',
                          background: '#ff6b6b',
                          borderRadius: '4px',
                          width: `${benchmarks.global_percentiles.guardrail_tax_ms.your_percentile}%`,
                        }}
                      ></div>
                    </div>
                    <p style={{ fontSize: '0.85rem', color: '#ccc', margin: 0 }}>
                      {benchmarks.global_percentiles.guardrail_tax_ms.message}
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div className="insights-panel">
              <h2>Diagnostic Resolution Directives</h2>
              {insights.map((insight, idx) => (
                <div key={idx} className={`insight-card severity-${insight.severity}`}>
                  <div className="insight-header">
                    <span className="insight-metric">{insight.metric}</span>
                    {insight.severity === 'critical' && <span className="alert-badge">Critical</span>}
                  </div>
                  <p className="insight-observation">{insight.observation}</p>
                  <p className="insight-observation">
                    Evidence: {insight.sample_size.toLocaleString()} samples · {(insight.confidence * 100).toFixed(0)}%
                    confidence
                  </p>
                  <div className="insight-prescription">
                    <strong>Action Required:</strong> {insight.prescription}
                  </div>
                  {insight.estimated_savings_usd_per_10k > 0 && (
                    <div className="insight-savings">
                      Estimated Savings:{' '}
                      <span className="savings-value">+${insight.estimated_savings_usd_per_10k}/mo</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'safeguards' && (
        <div className="safeguards-view" style={{ padding: '2rem', background: '#1e1e1e', borderRadius: '8px' }}>
          <h2>Safeguard Shells Policy Governance</h2>
          <p>Configure dynamic circuit breakers and PII redaction policies for this tenant.</p>

          {policyMessage && (
            <div
              style={{
                marginTop: '1rem',
                padding: '0.75rem 1rem',
                borderRadius: '4px',
                background: policyMessage.includes('Failed') ? '#c0392b' : '#27ae60',
                color: 'white',
              }}
            >
              {policyMessage}
            </div>
          )}

          <div style={{ marginTop: '2rem' }}>
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                Max Acceptable Guardrail Tax (Minutes)
              </label>
              <input
                type="number"
                value={maxTax}
                onChange={(e) => setMaxTax(parseFloat(e.target.value) || 0)}
                step="0.1"
                style={{
                  padding: '0.5rem',
                  width: '200px',
                  background: '#333',
                  color: 'white',
                  border: '1px solid #555',
                  borderRadius: '4px',
                }}
              />
              <p style={{ fontSize: '0.85rem', color: '#aaa', marginTop: '0.25rem' }}>
                If a telemetry event reports latency higher than this, the circuit breaker intervenes to protect ROI.
              </p>
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label
                style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 'bold', cursor: 'pointer' }}
              >
                <input
                  type="checkbox"
                  checked={piiEnabled}
                  onChange={(e) => setPiiEnabled(e.target.checked)}
                  style={{ width: '18px', height: '18px' }}
                />
                Enable PII Redaction
              </label>
              <p style={{ fontSize: '0.85rem', color: '#aaa', marginTop: '0.25rem' }}>
                Automatically scrub emails, SSNs, credit cards, and sensitive tokens from all telemetry before storage.
              </p>
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label
                style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 'bold', cursor: 'pointer' }}
              >
                <input
                  type="checkbox"
                  checked={strictMode}
                  onChange={(e) => setStrictMode(e.target.checked)}
                  style={{ width: '18px', height: '18px' }}
                />
                Enforce Strict Mode (Halt on Breach)
              </label>
              <p style={{ fontSize: '0.85rem', color: '#aaa', marginTop: '0.25rem' }}>
                When enabled, events exceeding maximum latency tax will be strictly rejected with an error.
              </p>
            </div>

            <button
              onClick={handleSavePolicy}
              disabled={savingPolicy}
              style={{
                padding: '0.75rem 1.5rem',
                background: '#6c5ce7',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: 'bold',
              }}
            >
              {savingPolicy ? 'Saving...' : 'Save Policy Configuration'}
            </button>
          </div>
        </div>
      )}

      {activeTab === 'workspaces' && (
        <div className="workspaces-view" style={{ padding: '2rem', background: '#1e1e1e', borderRadius: '8px' }}>
          <h2>Multi-Tenant Workspaces (RBAC)</h2>
          <p>Manage organizations, active environments, and API credentials.</p>

          <table style={{ width: '100%', marginTop: '2rem', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #444' }}>
                <th style={{ padding: '1rem 0' }}>Workspace</th>
                <th>Role</th>
                <th>API Key Ref</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {workspaces.map((w) => (
                <tr key={w.id} style={{ borderBottom: '1px solid #333' }}>
                  <td style={{ padding: '1rem 0', fontWeight: 'bold' }}>{w.name}</td>
                  <td>
                    <span
                      style={{ background: '#444', padding: '0.25rem 0.5rem', borderRadius: '4px', fontSize: '0.8rem' }}
                    >
                      {w.role}
                    </span>
                  </td>
                  <td>
                    <code>{w.key}</code>
                  </td>
                  <td>
                    <span style={{ color: '#82ca9d' }}>{w.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <button
            onClick={() => setShowModal(true)}
            style={{
              marginTop: '2rem',
              padding: '0.75rem 1.5rem',
              background: '#6c5ce7',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 'bold',
            }}
          >
            + Provision New Workspace
          </button>

          {showModal && (
            <div
              style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(0,0,0,0.7)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 1000,
              }}
            >
              <div
                style={{
                  background: '#1e1e1e',
                  padding: '2rem',
                  borderRadius: '8px',
                  width: '450px',
                  maxWidth: '90%',
                  border: '1px solid #444',
                }}
              >
                <h3>Provision Organization Workspace</h3>
                {createdKey ? (
                  <div style={{ marginTop: '1rem' }}>
                    <p style={{ color: '#82ca9d' }}>Workspace created successfully! Save your API key now:</p>
                    <div
                      style={{
                        background: '#111',
                        padding: '0.75rem',
                        borderRadius: '4px',
                        wordBreak: 'break-all',
                        fontFamily: 'monospace',
                        margin: '1rem 0',
                        userSelect: 'all',
                      }}
                    >
                      {createdKey}
                    </div>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(createdKey);
                        alert('API Key copied to clipboard!');
                      }}
                      style={{
                        padding: '0.5rem 1rem',
                        background: '#6c5ce7',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        marginRight: '0.5rem',
                      }}
                    >
                      Copy Key
                    </button>
                    <button
                      onClick={() => {
                        setShowModal(false);
                        setCreatedKey(null);
                      }}
                      style={{
                        padding: '0.5rem 1rem',
                        background: '#333',
                        color: '#ccc',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                      }}
                    >
                      Close
                    </button>
                  </div>
                ) : (
                  <form onSubmit={handleProvisionWorkspace} style={{ marginTop: '1.5rem' }}>
                    <div style={{ marginBottom: '1rem' }}>
                      <label style={{ display: 'block', marginBottom: '0.5rem' }}>Organization Name</label>
                      <input
                        type="text"
                        placeholder="e.g. Acme FinTech"
                        value={newOrgName}
                        onChange={(e) => setNewOrgName(e.target.value)}
                        required
                        style={{
                          width: '100%',
                          padding: '0.5rem',
                          background: '#333',
                          color: 'white',
                          border: '1px solid #555',
                          borderRadius: '4px',
                        }}
                      />
                    </div>
                    <div style={{ marginBottom: '1.5rem' }}>
                      <label style={{ display: 'block', marginBottom: '0.5rem' }}>Subscription Tier</label>
                      <select
                        value={newOrgTier}
                        onChange={(e) => setNewOrgTier(e.target.value)}
                        style={{
                          width: '100%',
                          padding: '0.5rem',
                          background: '#333',
                          color: 'white',
                          border: '1px solid #555',
                          borderRadius: '4px',
                        }}
                      >
                        <option value="community">Community</option>
                        <option value="team">Team ($99/mo)</option>
                        <option value="business">Business ($499/mo)</option>
                        <option value="enterprise">Enterprise (Custom)</option>
                      </select>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                      <button
                        type="button"
                        onClick={() => setShowModal(false)}
                        style={{
                          padding: '0.5rem 1rem',
                          background: '#333',
                          color: '#ccc',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                        }}
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={provisioning}
                        style={{
                          padding: '0.5rem 1rem',
                          background: '#6c5ce7',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                        }}
                      >
                        {provisioning ? 'Provisioning...' : 'Provision'}
                      </button>
                    </div>
                  </form>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;

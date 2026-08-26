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

interface MetricsData {
  telemetry_count: number;
  evaluation_count: number;
  avg_gross_time_saved_min: number;
  avg_guardrail_tax_min: number;
  avg_rag_reliability_coefficient: number;
  macro_tvy_min: number;
  avg_true_value_yield_usd: number | null;
  is_net_positive: boolean;
}

interface Insight {
  severity: 'info' | 'high' | 'critical';
  metric: string;
  observation: string;
  prescription: string;
  estimated_savings_usd_per_10k: number;
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

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [benchmarks, setBenchmarks] = useState<BenchmarksData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState<string>('');
  const [loginError, setLoginError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'safeguards' | 'workspaces'>('overview');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await axios.post('http://localhost:8000/api/v1/auth/sso/login', {
        email: email,
        connection: 'saml-okta'
      });
      if (res.data.access_token) {
        localStorage.setItem('apva_token', res.data.access_token);
        setIsAuthenticated(true);
      }
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setLoginError(err.response?.data?.detail || 'SSO Login Failed');
      } else {
        setLoginError('An unexpected error occurred');
      }
    }
  };

  useEffect(() => {
    if (!isAuthenticated) return;
    
    const fetchData = async () => {
      setLoading(true);
      try {
        const token = localStorage.getItem('apva_token') || 'APVA-DEV-KEY-123';
        const headers = { 'Authorization': `Bearer ${token}` };
        
        const [metricsRes, insightsRes, benchmarksRes] = await Promise.all([
          axios.get('http://localhost:8000/api/v1/metrics/tvy', { headers }),
          axios.get('http://localhost:8000/api/v1/metrics/insights', { headers }),
          axios.get('http://localhost:8000/api/v1/metrics/benchmarks', { headers })
        ]);
        
        setMetrics(metricsRes.data);
        setInsights(insightsRes.data);
        setBenchmarks(benchmarksRes.data);
        setLoading(false);
      } catch (err: unknown) {
        if (err instanceof Error) {
          setError(err.message || 'Failed to fetch metrics');
        } else {
          setError('An unknown error occurred');
        }
        setLoading(false);
      }
    };
    
    fetchData();
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return (
      <div className="login-container">
        <div className="login-card">
          <h1>APVA Analytical Engine</h1>
          <p>Authenticate via organizational identity provider</p>
          <form onSubmit={handleLogin} className="login-form">
            <input 
              type="email" 
              placeholder="name@acmecorp.com" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            {loginError && <div className="login-error">{loginError}</div>}
            <button type="submit">Continue with SSO / SAML</button>
          </form>
        </div>
      </div>
    );
  }

  if (loading) return <div className="loader">Initializing APVA Analytical Engine...</div>;
  if (error) return <div className="error">Metrics resolution failure: {error}</div>;

  // Mock historical data
  const mockHistoricalData = [
    { name: 'Mon', tvy: (metrics?.macro_tvy_min ?? 0) * 0.8, tvyUsd: (metrics?.avg_true_value_yield_usd ?? 0) * 0.8 },
    { name: 'Tue', tvy: (metrics?.macro_tvy_min ?? 0) * 0.9, tvyUsd: (metrics?.avg_true_value_yield_usd ?? 0) * 0.9 },
    { name: 'Wed', tvy: (metrics?.macro_tvy_min ?? 0) * 1.1, tvyUsd: (metrics?.avg_true_value_yield_usd ?? 0) * 1.1 },
    { name: 'Thu', tvy: (metrics?.macro_tvy_min ?? 0) * 1.05, tvyUsd: (metrics?.avg_true_value_yield_usd ?? 0) * 1.05 },
    { name: 'Fri', tvy: metrics?.macro_tvy_min ?? 0, tvyUsd: metrics?.avg_true_value_yield_usd ?? 0 },
  ];

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div className="tenant-badge">Organization: Acme Corp</div>
        <h1>APVA True Value Yield Dashboard</h1>
        <p>Enterprise Inference Analytics & Operational Directives</p>
        <div className="tabs" style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
          <button style={{ padding: '0.5rem 1rem', background: activeTab === 'overview' ? '#4a4a4a' : '#2a2a2a', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }} onClick={() => setActiveTab('overview')}>Overview</button>
          <button style={{ padding: '0.5rem 1rem', background: activeTab === 'safeguards' ? '#4a4a4a' : '#2a2a2a', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }} onClick={() => setActiveTab('safeguards')}>Safeguard Policies</button>
          <button style={{ padding: '0.5rem 1rem', background: activeTab === 'workspaces' ? '#4a4a4a' : '#2a2a2a', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }} onClick={() => setActiveTab('workspaces')}>Workspaces</button>
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
                <div className="metric-value">{(metrics?.avg_rag_reliability_coefficient ?? 0 * 100).toFixed(1)}%</div>
              </div>
            </div>

            <div className="chart-container">
              <h2>TVY Trending (Last 5 Days)</h2>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={mockHistoricalData}>
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
                  <div className="benchmark-card" style={{ padding: '1rem', background: '#252526', borderRadius: '8px', marginBottom: '1rem' }}>
                    <h4 style={{ margin: '0 0 0.5rem 0' }}>RAG Reliability (p{benchmarks.global_percentiles.rag_reliability.your_percentile})</h4>
                    <div style={{ height: '8px', background: '#333', borderRadius: '4px', marginBottom: '0.5rem' }}>
                      <div style={{ height: '100%', background: '#82ca9d', borderRadius: '4px', width: `${benchmarks.global_percentiles.rag_reliability.your_percentile}%` }}></div>
                    </div>
                    <p style={{ fontSize: '0.85rem', color: '#ccc', margin: 0 }}>{benchmarks.global_percentiles.rag_reliability.message}</p>
                  </div>
                  <div className="benchmark-card" style={{ padding: '1rem', background: '#252526', borderRadius: '8px' }}>
                    <h4 style={{ margin: '0 0 0.5rem 0' }}>Guardrail Tax (p{benchmarks.global_percentiles.guardrail_tax_ms.your_percentile})</h4>
                    <div style={{ height: '8px', background: '#333', borderRadius: '4px', marginBottom: '0.5rem' }}>
                      <div style={{ height: '100%', background: '#ff6b6b', borderRadius: '4px', width: `${benchmarks.global_percentiles.guardrail_tax_ms.your_percentile}%` }}></div>
                    </div>
                    <p style={{ fontSize: '0.85rem', color: '#ccc', margin: 0 }}>{benchmarks.global_percentiles.guardrail_tax_ms.message}</p>
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
                  <div className="insight-prescription">
                    <strong>Action Required:</strong> {insight.prescription}
                  </div>
                  {insight.estimated_savings_usd_per_10k > 0 && (
                    <div className="insight-savings">
                      Estimated Savings: <span className="savings-value">+${insight.estimated_savings_usd_per_10k}/mo</span>
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
          <div style={{ marginTop: '2rem' }}>
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Max Acceptable Guardrail Tax (Minutes)</label>
              <input type="number" defaultValue="2.0" step="0.1" style={{ padding: '0.5rem', width: '200px', background: '#333', color: 'white', border: '1px solid #555', borderRadius: '4px' }} />
              <p style={{ fontSize: '0.85rem', color: '#aaa', marginTop: '0.25rem' }}>If a telemetry event reports latency higher than this, the circuit breaker halts evaluation to protect ROI.</p>
            </div>
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 'bold', cursor: 'pointer' }}>
                <input type="checkbox" defaultChecked style={{ width: '18px', height: '18px' }} />
                Enable PII Redaction
              </label>
              <p style={{ fontSize: '0.85rem', color: '#aaa', marginTop: '0.25rem' }}>Automatically scrub emails, SSNs, and sensitive data from all logs before they hit APVA Storage or Kafka.</p>
            </div>
            <button style={{ padding: '0.75rem 1.5rem', background: '#8884d8', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>Save Policy Configuration</button>
          </div>
        </div>
      )}

      {activeTab === 'workspaces' && (
        <div className="workspaces-view" style={{ padding: '2rem', background: '#1e1e1e', borderRadius: '8px' }}>
          <h2>Multi-Tenant Workspaces (RBAC)</h2>
          <p>Manage environments, API keys, and team member access roles.</p>
          <table style={{ width: '100%', marginTop: '2rem', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #444' }}>
                <th style={{ padding: '1rem 0' }}>Workspace</th>
                <th>Role</th>
                <th>API Keys</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid #333' }}>
                <td style={{ padding: '1rem 0', fontWeight: 'bold' }}>Production</td>
                <td><span style={{ background: '#444', padding: '0.25rem 0.5rem', borderRadius: '4px', fontSize: '0.8rem' }}>Admin</span></td>
                <td><code>pk_live_...482</code></td>
                <td><span style={{ color: '#82ca9d' }}>Active</span></td>
              </tr>
              <tr>
                <td style={{ padding: '1rem 0', fontWeight: 'bold' }}>Staging / Dev</td>
                <td><span style={{ background: '#444', padding: '0.25rem 0.5rem', borderRadius: '4px', fontSize: '0.8rem' }}>Editor</span></td>
                <td><code>pk_test_...19f</code></td>
                <td><span style={{ color: '#82ca9d' }}>Active</span></td>
              </tr>
            </tbody>
          </table>
          <button style={{ marginTop: '2rem', padding: '0.75rem 1.5rem', background: '#2a2a2a', color: 'white', border: '1px solid #555', borderRadius: '4px', cursor: 'pointer' }}>+ Provision New Workspace</button>
        </div>
      )}
    </div>
  );
}

export default App;

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

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState<string>('');
  const [loginError, setLoginError] = useState<string | null>(null);

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
        
        const [metricsRes, insightsRes] = await Promise.all([
          axios.get('http://localhost:8000/api/v1/metrics/tvy', { headers }),
          axios.get('http://localhost:8000/api/v1/metrics/insights', { headers })
        ]);
        
        setMetrics(metricsRes.data);
        setInsights(insightsRes.data);
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
      </header>
      
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
    </div>
  );
}

export default App;

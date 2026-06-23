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

function App() {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // In a real app, you would pass the API key via headers or context
    // This expects the backend to be running at localhost:8000
    axios.get('http://localhost:8000/api/v1/metrics/tvy', {
        headers: { 'Authorization': 'Bearer APVA-DEV-KEY-123' }
    })
      .then(response => {
        setMetrics(response.data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message || 'Failed to fetch metrics');
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="loader">Loading APVA Dashboard...</div>;
  if (error) return <div className="error">Error loading metrics: {error}</div>;

  // Mock historical data since the endpoint only provides a snapshot
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
        <h1>APVA True Value Yield Dashboard</h1>
        <p>Enterprise AI ROI Analytics</p>
      </header>
      
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
  );
}

export default App;

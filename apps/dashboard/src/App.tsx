import React, { lazy, Suspense, useEffect, useState } from 'react';
import axios from 'axios';
import type { TimeseriesPoint } from './TvyTrendChart';
import {
  ApvaLogo,
  ZapIcon,
  ChartBarIcon,
  ShieldCheckIcon,
  LayersIcon,
  TrendingUpIcon,
  DollarSignIcon,
  ClockIcon,
  ActivityIcon,
  CpuIcon,
  CopyIcon,
  CheckIcon,
  AlertTriangleIcon,
  LogOutIcon,
  ChevronRightIcon,
  SlidersIcon,
  PlusIcon,
} from './Icons';
import './App.css';

const API_BASE = import.meta.env.VITE_API_URL || '';
const TvyTrendChart = lazy(() => import('./TvyTrendChart'));

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

interface TenantProfile {
  id: number;
  name: string;
  tier: string;
  created_at: string;
}

interface BusinessCaseReport {
  report_id: string;
  decision: 'scale' | 'controlled_pilot' | 'optimize' | 'do_not_scale';
  priority_score: number;
  annual_task_volume: number;
  first_year_net_value_usd: number;
  recurring_annual_net_value_usd: number;
  net_present_value_usd: number;
  first_year_roi_pct: number | null;
  payback_months: number | null;
  positive_scenario_rate: number | null;
  monthly_cost_of_delay_usd: number;
  downside_tvy_min: number;
  upside_tvy_min: number;
  x_factor_annual_value_usd: number;
  causal_value_yield_per_task_usd: number;
  coordination_dividend_per_task_usd: number;
  knowledge_dividend_per_task_usd: number;
  expected_downstream_loss_per_task_usd: number;
  probability_negative_tvy: number;
  conditional_value_at_risk_5_min: number;
  enterprise_value_capture_rate: number;
  trust_adjusted_autonomy_rate: number;
  gate_checks: Array<{
    check: string;
    label: string;
    passed: boolean;
    actual: number | null;
    operator: string;
    threshold: number;
    unit: string;
  }>;
  top_levers: Array<{
    parameter: string;
    direction: string;
    estimated_tvy_gain_min: number;
    sensitivity_span_min: number;
  }>;
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
  const [activeTab, setActiveTab] = useState<'overview' | 'value-studio' | 'safeguards' | 'workspaces'>('overview');

  // Enterprise Value Studio state
  const [useCaseName, setUseCaseName] = useState<string>('Enterprise AI Workflow');
  const [practitioners, setPractitioners] = useState<number>(250);
  const [tasksPerDay, setTasksPerDay] = useState<number>(4);
  const [adoptionRate, setAdoptionRate] = useState<number>(65);
  const [implementationCost, setImplementationCost] = useState<number>(75000);
  const [annualPlatformCost, setAnnualPlatformCost] = useState<number>(60000);
  const [variableTaskCost, setVariableTaskCost] = useState<number>(0.15);
  const [riskAvoidance, setRiskAvoidance] = useState<number>(25000);
  const [causalConfidence, setCausalConfidence] = useState<number>(75);
  const [coordinationMinutes, setCoordinationMinutes] = useState<number>(1.5);
  const [reusableOutputRate, setReusableOutputRate] = useState<number>(20);
  const [expectedReuses, setExpectedReuses] = useState<number>(2);
  const [minutesPerReuse, setMinutesPerReuse] = useState<number>(4);
  const [escapedErrorRate, setEscapedErrorRate] = useState<number>(0.2);
  const [escapedErrorLoss, setEscapedErrorLoss] = useState<number>(500);
  const [blastRadius, setBlastRadius] = useState<number>(1.5);
  const [autonomousRate, setAutonomousRate] = useState<number>(50);
  const [humanOverrideRate, setHumanOverrideRate] = useState<number>(10);
  const [businessCase, setBusinessCase] = useState<BusinessCaseReport | null>(null);
  const [analyzingCase, setAnalyzingCase] = useState<boolean>(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

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
  const [copiedKey, setCopiedKey] = useState<boolean>(false);
  const [copiedAudit, setCopiedAudit] = useState<boolean>(false);

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

  const handleAnalyzeBusinessCase = async (e: React.FormEvent) => {
    e.preventDefault();
    setAnalyzingCase(true);
    setAnalysisError(null);
    try {
      const response = await axios.post(
        `${API_BASE}/api/v1/analysis/observed-business-case`,
        {
          use_case_name: useCaseName,
          business_case: {
            organization: tenantProfile?.name || 'Enterprise',
            use_case_owner: 'AI Transformation Office',
            practitioners,
            tasks_per_practitioner_per_day: tasksPerDay,
            working_days_per_year: 230,
            adoption_rate: adoptionRate / 100,
            realization_rate: 0.8,
            evidence_confidence: 0.8,
            implementation_cost_usd: implementationCost,
            annual_platform_cost_usd: annualPlatformCost,
            variable_ai_cost_per_task_usd: variableTaskCost,
            annual_risk_avoidance_usd: riskAvoidance,
            analysis_years: 3,
            discount_rate: 0.1,
          },
          x_factors: {
            causal_attribution_method: 'pre_post',
            causal_attribution_confidence: causalConfidence / 100,
            coordination_minutes_saved_per_task: coordinationMinutes,
            reusable_output_rate: reusableOutputRate / 100,
            expected_reuses_per_output: expectedReuses,
            minutes_saved_per_reuse: minutesPerReuse,
            escaped_error_probability: escapedErrorRate / 100,
            loss_per_escaped_error_usd: escapedErrorLoss,
            downstream_blast_radius_multiplier: blastRadius,
            autonomous_completion_rate: autonomousRate / 100,
            human_override_rate: humanOverrideRate / 100,
          },
          monte_carlo_simulations: 1000,
        },
        { headers: getAuthHeaders() }
      );
      setBusinessCase(response.data);
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setAnalysisError(err.response?.data?.detail || err.message);
      } else {
        setAnalysisError('Unable to generate the enterprise business case.');
      }
    } finally {
      setAnalyzingCase(false);
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

  const copyToClipboard = (text: string, isKey = false) => {
    navigator.clipboard.writeText(text);
    if (isKey) {
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
    } else {
      setCopiedAudit(true);
      setTimeout(() => setCopiedAudit(false), 2000);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="login-container">
        <div className="login-card">
          <div className="login-logo-wrap">
            <ApvaLogo size={52} />
          </div>
          <h1>APVA Analytical Engine</h1>
          <p>Quantum True Value Yield & Value Architecture Terminal</p>

          <div className="auth-mode-switch">
            <button
              type="button"
              className={`auth-mode-btn ${authMode === 'sso' ? 'active' : ''}`}
              onClick={() => setAuthMode('sso')}
            >
              SSO / Enterprise SAML
            </button>
            <button
              type="button"
              className={`auth-mode-btn ${authMode === 'apikey' ? 'active' : ''}`}
              onClick={() => setAuthMode('apikey')}
            >
              Developer API Key
            </button>
          </div>

          <form onSubmit={handleLogin} className="login-form">
            {authMode === 'sso' ? (
              <input
                type="email"
                className="login-input"
                placeholder="name@enterprise.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            ) : (
              <input
                type="password"
                className="login-input"
                placeholder="apva_live_..."
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                required
              />
            )}
            {loginError && <div className="login-error">{loginError}</div>}
            <button type="submit" className="login-submit-btn">
              <span>{authMode === 'sso' ? 'Continue with SSO Identity' : 'Authenticate Quantum Key'}</span>
              <ChevronRightIcon size={16} />
            </button>
          </form>
        </div>
      </div>
    );
  }

  if (loading) return <div className="loader">INITIALIZING APVA ANALYTICAL TERMINAL...</div>;
  if (error) return <div className="error">METRICS RESOLUTION FAILURE: {error}</div>;

  return (
    <div className="dashboard-container">
      {/* Top Bar with Brand & Telemetry Status */}
      <header className="dashboard-header">
        <div className="top-bar">
          <div className="brand-section">
            <div className="brand-logo-glow">
              <ApvaLogo size={32} />
            </div>
            <div className="brand-titles">
              <div className="brand-name">
                APVA Terminal
              </div>
              <div className="brand-tagline">Quantum True Value Yield Architecture</div>
            </div>
          </div>

          <div className="top-bar-actions">
            <div className="tenant-pill">
              <div className="live-indicator-dot" />
              <span>Org: <strong>{tenantProfile?.name || 'Default Organization'}</strong></span>
              <span className="tier-chip">{tenantProfile?.tier || 'Community'}</span>
            </div>
            <button className="signout-btn" onClick={handleLogout} title="Sign Out">
              <LogOutIcon size={14} />
              <span>Sign Out</span>
            </button>
          </div>
        </div>

        {/* Floating Navigation Pill Group */}
        <nav className="nav-pill-group">
          <button
            className={`nav-pill-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <ChartBarIcon size={16} />
            <span>Yield Overview</span>
          </button>
          <button
            className={`nav-pill-btn ${activeTab === 'value-studio' ? 'active' : ''}`}
            onClick={() => setActiveTab('value-studio')}
          >
            <ZapIcon size={16} />
            <span>Value Studio</span>
          </button>
          <button
            className={`nav-pill-btn ${activeTab === 'safeguards' ? 'active' : ''}`}
            onClick={() => setActiveTab('safeguards')}
          >
            <ShieldCheckIcon size={16} />
            <span>Safeguard Policies</span>
          </button>
          <button
            className={`nav-pill-btn ${activeTab === 'workspaces' ? 'active' : ''}`}
            onClick={() => setActiveTab('workspaces')}
          >
            <LayersIcon size={16} />
            <span>Workspaces</span>
          </button>
        </nav>
      </header>

      {/* OVERVIEW TAB */}
      {activeTab === 'overview' && (
        <div className="layout-grid">
          <div className="main-content">
            {/* 8 Holographic Metric Cards */}
            <div className="metrics-grid">
              <div className={`metric-card ${metrics?.is_net_positive ? 'positive' : 'negative'}`}>
                <div className="metric-card-top">
                  <h3>Macro TVY</h3>
                  <div className="metric-card-icon"><ClockIcon size={16} /></div>
                </div>
                <div className="metric-value">{metrics?.macro_tvy_min != null ? `${metrics.macro_tvy_min.toFixed(2)}m` : '0.00m'}</div>
                <div className="metric-card-meta">Net operational yield / event</div>
              </div>

              <div className={`metric-card ${metrics?.is_net_positive ? 'positive' : 'negative'}`}>
                <div className="metric-card-top">
                  <h3>Financial TVY</h3>
                  <div className="metric-card-icon"><DollarSignIcon size={16} /></div>
                </div>
                <div className="metric-value">{metrics?.avg_true_value_yield_usd != null ? `$${metrics.avg_true_value_yield_usd.toFixed(2)}` : '$0.00'}</div>
                <div className="metric-card-meta">Realized cash equivalent yield</div>
              </div>

              <div className="metric-card">
                <div className="metric-card-top">
                  <h3>Avg Guardrail Tax</h3>
                  <div className="metric-card-icon"><ShieldCheckIcon size={16} /></div>
                </div>
                <div className="metric-value">{metrics?.avg_guardrail_tax_min != null ? `${metrics.avg_guardrail_tax_min.toFixed(2)}m` : '0.00m'}</div>
                <div className="metric-card-meta">Latency overhead consumed</div>
              </div>

              <div className="metric-card">
                <div className="metric-card-top">
                  <h3>RAG Reliability</h3>
                  <div className="metric-card-icon"><ActivityIcon size={16} /></div>
                </div>
                <div className="metric-value">
                  {metrics?.avg_rag_reliability_coefficient != null ? `${(metrics.avg_rag_reliability_coefficient * 100).toFixed(1)}%` : '0.0%'}
                </div>
                <div className="metric-card-meta">Context precision coefficient</div>
              </div>

              <div className={`metric-card ${metrics?.is_net_positive ? 'positive' : 'negative'}`}>
                <div className="metric-card-top">
                  <h3>Total Value Captured</h3>
                  <div className="metric-card-icon"><TrendingUpIcon size={16} /></div>
                </div>
                <div className="metric-value">{metrics?.total_tvy_usd != null ? `$${metrics.total_tvy_usd.toFixed(2)}` : '$0.00'}</div>
                <div className="metric-card-meta">Cumulative tenant return</div>
              </div>

              <div className="metric-card">
                <div className="metric-card-top">
                  <h3>Observed Runs</h3>
                  <div className="metric-card-icon"><CpuIcon size={16} /></div>
                </div>
                <div className="metric-value">{metrics?.telemetry_count != null ? metrics.telemetry_count.toLocaleString() : '0'}</div>
                <div className="metric-card-meta">Tracked enterprise executions</div>
              </div>

              <div className="metric-card">
                <div className="metric-card-top">
                  <h3>Financial Coverage</h3>
                  <div className="metric-card-icon"><DollarSignIcon size={16} /></div>
                </div>
                <div className="metric-value">{metrics?.hourly_rate_coverage != null ? `${(metrics.hourly_rate_coverage * 100).toFixed(1)}%` : '0.0%'}</div>
                <div className="metric-card-meta">Attributed workforce compensation</div>
              </div>

              <div className="metric-card">
                <div className="metric-card-top">
                  <h3>Shadow Event Rate</h3>
                  <div className="metric-card-icon"><AlertTriangleIcon size={16} /></div>
                </div>
                <div className="metric-value">{metrics?.shadow_event_rate != null ? `${(metrics.shadow_event_rate * 100).toFixed(1)}%` : '0.0%'}</div>
                <div className="metric-card-meta">Unmonitored agent activity</div>
              </div>
            </div>

            {/* Recharts Trending Curve */}
            <div className="chart-container">
              <div className="chart-header">
                <h2>
                  <TrendingUpIcon size={20} color="#00d9ff" />
                  <span>TVY Trending Dynamics</span>
                </h2>
                <div className="chart-live-badge">
                  <div className="live-indicator-dot" />
                  <span>Last 5 Days (Live Telemetry)</span>
                </div>
              </div>
              <Suspense fallback={<div className="chart-loading">Synthesizing quantum timeseries…</div>}>
                <TvyTrendChart data={timeseries} />
              </Suspense>
            </div>
          </div>

          {/* Sidebar: Benchmarks & Diagnostics */}
          <div className="sidebar">
            <div className="benchmarks-panel">
              <h2>
                <SlidersIcon size={18} color="#8b5cf6" />
                <span>Reference Thresholds</span>
              </h2>
              {benchmarks && (
                <div className="benchmark-cards">
                  <div className="benchmark-card">
                    <h4>
                      <span>RAG Reliability</span>
                      <span className="benchmark-score-chip">p{benchmarks.global_percentiles.rag_reliability.your_percentile}</span>
                    </h4>
                    <div className="progress-track">
                      <div
                        className="progress-bar-fill"
                        style={{
                          width: `${benchmarks.global_percentiles.rag_reliability.your_percentile}%`,
                          background: 'linear-gradient(90deg, #8b5cf6, #00f5a0)',
                        }}
                      />
                    </div>
                    <p className="benchmark-desc">
                      {benchmarks.global_percentiles.rag_reliability.message}
                    </p>
                  </div>

                  <div className="benchmark-card">
                    <h4>
                      <span>Guardrail Tax Overhead</span>
                      <span className="benchmark-score-chip">p{benchmarks.global_percentiles.guardrail_tax_ms.your_percentile}</span>
                    </h4>
                    <div className="progress-track">
                      <div
                        className="progress-bar-fill"
                        style={{
                          width: `${benchmarks.global_percentiles.guardrail_tax_ms.your_percentile}%`,
                          background: 'linear-gradient(90deg, #f59e0b, #ff3366)',
                        }}
                      />
                    </div>
                    <p className="benchmark-desc">
                      {benchmarks.global_percentiles.guardrail_tax_ms.message}
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div className="insights-panel">
              <h2>
                <AlertTriangleIcon size={18} color="#00d9ff" />
                <span>Resolution Directives</span>
              </h2>
              {insights.map((insight, idx) => (
                <div key={idx} className={`insight-card severity-${insight.severity}`}>
                  <div className="insight-header">
                    <span className="insight-metric">{insight.metric}</span>
                    <span className={`alert-badge ${insight.severity}`}>
                      {insight.severity}
                    </span>
                  </div>
                  <p className="insight-observation">{insight.observation}</p>
                  <div className="insight-evidence">
                    EVIDENCE: {insight.sample_size != null ? insight.sample_size.toLocaleString() : '0'} runs · {insight.confidence != null ? (insight.confidence * 100).toFixed(0) : '0'}% confidence
                  </div>
                  <div className="insight-prescription">
                    <strong>Direct Action:</strong> {insight.prescription}
                  </div>
                  {Boolean(insight.estimated_savings_usd_per_10k && insight.estimated_savings_usd_per_10k > 0) && (
                    <div className="insight-savings">
                      <span>PROJECTED SAVINGS</span>
                      <span className="savings-value">+${insight.estimated_savings_usd_per_10k.toLocaleString()}/mo</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* VALUE STUDIO TAB */}
      {activeTab === 'value-studio' && (
        <div className="studio-grid">
          <form className="studio-panel" onSubmit={handleAnalyzeBusinessCase}>
            <div className="studio-kicker">
              <ZapIcon size={14} />
              <span>LIVE TELEMETRY → INVESTMENT DECISION</span>
            </div>
            <h2>Enterprise Value Studio</h2>
            <p>
              Stress-test observed workflow performance against adoption curves, workforce scale, implementation capital, and operating unit economics.
            </p>

            <div className="studio-form-grid">
              <div className="studio-field">
                <label>Use Case Title</label>
                <input
                  type="text"
                  value={useCaseName}
                  onChange={(e) => setUseCaseName(e.target.value)}
                  required
                />
              </div>

              <div className="studio-field">
                <label>Practitioners</label>
                <input
                  type="number"
                  min="1"
                  value={practitioners}
                  onChange={(e) => setPractitioners(Number(e.target.value))}
                  required
                />
              </div>

              <div className="studio-field">
                <label>Tasks / Person / Day</label>
                <input
                  type="number"
                  min="0.1"
                  step="0.1"
                  value={tasksPerDay}
                  onChange={(e) => setTasksPerDay(Number(e.target.value))}
                  required
                />
              </div>

              <div className="studio-field">
                <label>
                  <span>Adoption Curve</span>
                  <span className="studio-field-value">{adoptionRate}%</span>
                </label>
                <input
                  type="range"
                  className="studio-range"
                  min="5"
                  max="100"
                  step="5"
                  value={adoptionRate}
                  onChange={(e) => setAdoptionRate(Number(e.target.value))}
                />
              </div>

              <div className="studio-field">
                <label>Implementation Capital ($)</label>
                <input
                  type="number"
                  min="0"
                  value={implementationCost}
                  onChange={(e) => setImplementationCost(Number(e.target.value))}
                />
              </div>

              <div className="studio-field">
                <label>Annual Platform Cost ($)</label>
                <input
                  type="number"
                  min="0"
                  value={annualPlatformCost}
                  onChange={(e) => setAnnualPlatformCost(Number(e.target.value))}
                />
              </div>

              <div className="studio-field">
                <label>AI Cost / Task ($)</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={variableTaskCost}
                  onChange={(e) => setVariableTaskCost(Number(e.target.value))}
                />
              </div>

              <div className="studio-field">
                <label>Risk Avoidance ($)</label>
                <input
                  type="number"
                  min="0"
                  value={riskAvoidance}
                  onChange={(e) => setRiskAvoidance(Number(e.target.value))}
                />
              </div>
            </div>

            {/* X-Factor Value Signals Drawer */}
            <details className="x-factor-inputs">
              <summary>
                <SlidersIcon size={16} />
                <span>X-Factor Value Signals & Autonomy Multiplex</span>
              </summary>
              <p className="x-factor-desc">
                Fine-tune causal attribution confidence, coordination dividends, reusable artifact leverage, and blast radius exposure.
              </p>
              <div className="studio-form-grid">
                <div className="studio-field">
                  <label>
                    <span>Causal Attribution</span>
                    <span className="studio-field-value">{causalConfidence}%</span>
                  </label>
                  <input
                    type="range"
                    className="studio-range"
                    min="0"
                    max="100"
                    value={causalConfidence}
                    onChange={(e) => setCausalConfidence(Number(e.target.value))}
                  />
                </div>

                <div className="studio-field">
                  <label>Coordination Min / Task</label>
                  <input
                    type="number"
                    min="0"
                    step="0.1"
                    value={coordinationMinutes}
                    onChange={(e) => setCoordinationMinutes(Number(e.target.value))}
                  />
                </div>

                <div className="studio-field">
                  <label>
                    <span>Reusable Output Rate</span>
                    <span className="studio-field-value">{reusableOutputRate}%</span>
                  </label>
                  <input
                    type="range"
                    className="studio-range"
                    min="0"
                    max="100"
                    value={reusableOutputRate}
                    onChange={(e) => setReusableOutputRate(Number(e.target.value))}
                  />
                </div>

                <div className="studio-field">
                  <label>Downstream Reuses</label>
                  <input
                    type="number"
                    min="0"
                    step="0.1"
                    value={expectedReuses}
                    onChange={(e) => setExpectedReuses(Number(e.target.value))}
                  />
                </div>

                <div className="studio-field">
                  <label>Minutes Saved / Reuse</label>
                  <input
                    type="number"
                    min="0"
                    step="0.1"
                    value={minutesPerReuse}
                    onChange={(e) => setMinutesPerReuse(Number(e.target.value))}
                  />
                </div>

                <div className="studio-field">
                  <label>Escaped-Error Rate (%)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.01"
                    value={escapedErrorRate}
                    onChange={(e) => setEscapedErrorRate(Number(e.target.value))}
                  />
                </div>

                <div className="studio-field">
                  <label>Loss / Escaped Error ($)</label>
                  <input
                    type="number"
                    min="0"
                    value={escapedErrorLoss}
                    onChange={(e) => setEscapedErrorLoss(Number(e.target.value))}
                  />
                </div>

                <div className="studio-field">
                  <label>Blast Radius Multiplier</label>
                  <input
                    type="number"
                    min="1"
                    max="1000"
                    step="0.1"
                    value={blastRadius}
                    onChange={(e) => setBlastRadius(Number(e.target.value))}
                  />
                </div>

                <div className="studio-field">
                  <label>
                    <span>Autonomous Completion</span>
                    <span className="studio-field-value">{autonomousRate}%</span>
                  </label>
                  <input
                    type="range"
                    className="studio-range"
                    min="0"
                    max="100"
                    value={autonomousRate}
                    onChange={(e) => setAutonomousRate(Number(e.target.value))}
                  />
                </div>

                <div className="studio-field">
                  <label>
                    <span>Human Override Rate</span>
                    <span className="studio-field-value">{humanOverrideRate}%</span>
                  </label>
                  <input
                    type="range"
                    className="studio-range"
                    min="0"
                    max="100"
                    value={humanOverrideRate}
                    onChange={(e) => setHumanOverrideRate(Number(e.target.value))}
                  />
                </div>
              </div>
            </details>

            {analysisError && <div className="studio-error">{analysisError}</div>}

            <button className="studio-cta" type="submit" disabled={analyzingCase}>
              <ZapIcon size={18} />
              <span>{analyzingCase ? 'Executing 1,000 Monte Carlo Simulations…' : 'Generate Enterprise Business Case'}</span>
            </button>
          </form>

          {/* Results Side */}
          <section className="studio-results">
            {!businessCase ? (
              <div className="studio-empty">
                <div className="empty-radar-wrap">
                  <ZapIcon size={36} color="#00f5a0" />
                </div>
                <span>81 SCENARIOS</span>
                <strong>Awaiting Simulation Execution</strong>
                <p>Generate a case to calculate posture decision, downside CVaR, NPV, payback period, and governance gates.</p>
              </div>
            ) : (
              <>
                <div className={`decision-banner decision-${businessCase.decision}`}>
                  <div className="decision-label-group">
                    <span>RECOMMENDED POSTURE</span>
                    <strong>{businessCase.decision.replaceAll('_', ' ').toUpperCase()}</strong>
                  </div>
                  <div className="priority-score-dial">
                    <div className="priority-score">
                      {businessCase.priority_score}<small>/100</small>
                    </div>
                    <div className="priority-score-label">Priority Index</div>
                  </div>
                </div>

                <div className="studio-metrics">
                  <article>
                    <span>First-year net value</span>
                    <strong>${businessCase.first_year_net_value_usd.toLocaleString()}</strong>
                  </article>
                  <article>
                    <span>3-year NPV</span>
                    <strong>${businessCase.net_present_value_usd.toLocaleString()}</strong>
                  </article>
                  <article>
                    <span>First-year ROI</span>
                    <strong>{businessCase.first_year_roi_pct?.toFixed(0) || 'N/A'}%</strong>
                  </article>
                  <article>
                    <span>Payback</span>
                    <strong>{businessCase.payback_months?.toFixed(1) || 'N/A'} mo</strong>
                  </article>
                  <article>
                    <span>Scenario resilience</span>
                    <strong>{((businessCase.positive_scenario_rate || 0) * 100).toFixed(0)}%</strong>
                  </article>
                  <article>
                    <span>Cost of delay</span>
                    <strong>${businessCase.monthly_cost_of_delay_usd.toLocaleString()}/mo</strong>
                  </article>
                </div>

                <div className="x-factor-scorecard">
                  <h3>
                    <LayersIcon size={16} />
                    <span>Value Integrity Scorecard</span>
                  </h3>
                  <div className="studio-metrics">
                    <article>
                      <span>Enterprise value capture</span>
                      <strong>{(businessCase.enterprise_value_capture_rate * 100).toFixed(1)}%</strong>
                    </article>
                    <article>
                      <span>Trust-adjusted autonomy</span>
                      <strong>{(businessCase.trust_adjusted_autonomy_rate * 100).toFixed(1)}%</strong>
                    </article>
                    <article>
                      <span>Negative TVY probability</span>
                      <strong>{(businessCase.probability_negative_tvy * 100).toFixed(1)}%</strong>
                    </article>
                    <article>
                      <span>Worst 5% avg TVY</span>
                      <strong>{businessCase.conditional_value_at_risk_5_min.toFixed(2)}m</strong>
                    </article>
                    <article>
                      <span>Coordination + reuse / task</span>
                      <strong>${(businessCase.coordination_dividend_per_task_usd + businessCase.knowledge_dividend_per_task_usd).toFixed(2)}</strong>
                    </article>
                    <article>
                      <span>Downstream loss / task</span>
                      <strong>${businessCase.expected_downstream_loss_per_task_usd.toFixed(2)}</strong>
                    </article>
                  </div>
                </div>

                <div className="studio-detail-grid">
                  <div className="studio-detail-card">
                    <h3>Governance Policy Gates</h3>
                    {businessCase.gate_checks.map((gate) => (
                      <div className={`gate-row ${gate.passed ? 'gate-pass' : 'gate-fail'}`} key={gate.check}>
                        <span className="gate-icon">{gate.passed ? '✓' : '!'}</span>
                        <div>
                          <strong>{gate.label}</strong>
                          <small>Actual: {gate.actual ?? 'N/A'} {gate.unit} (Target {gate.operator} {gate.threshold})</small>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="studio-detail-card">
                    <h3>Top Sensitivity Levers</h3>
                    {businessCase.top_levers.slice(0, 5).map((lever, index) => (
                      <div className="lever-row" key={lever.parameter || index}>
                        <span className="lever-rank">{index + 1}</span>
                        <div>
                          <strong>{lever.parameter?.split('.').pop()?.replaceAll('_', ' ') || 'parameter'}</strong>
                          <small>{lever.direction || 'optimize'} · Span: {lever.sensitivity_span_min != null ? lever.sensitivity_span_min.toFixed(2) : '0.00'}m TVY</small>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="report-id-chip">
                  <span>AUDIT FINGERPRINT: {businessCase.report_id}</span>
                  <button
                    onClick={() => copyToClipboard(businessCase.report_id)}
                    style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', display: 'flex' }}
                    title="Copy Audit ID"
                  >
                    {copiedAudit ? <CheckIcon size={14} color="#00f5a0" /> : <CopyIcon size={14} />}
                  </button>
                </div>
              </>
            )}
          </section>
        </div>
      )}

      {/* SAFEGUARDS POLICY TAB */}
      {activeTab === 'safeguards' && (
        <div className="safeguards-view">
          <div className="safeguards-header">
            <h2>Safeguard Shells Policy Governance</h2>
            <p>Configure dynamic circuit breakers, latency tax ceilings, and automated PII redaction rules across the telemetry pipeline.</p>
          </div>

          <div className="policy-card-group">
            <div className="policy-card">
              <div className="policy-info">
                <div className="policy-title">
                  <ClockIcon size={18} color="#00d9ff" />
                  <span>Max Acceptable Guardrail Tax</span>
                </div>
                <div className="policy-desc">
                  When telemetry events observe latency overhead exceeding this threshold, the intelligent circuit breaker intervenes to prevent ROI deterioration.
                </div>
              </div>
              <div className="tax-input-wrap">
                <input
                  type="number"
                  className="tax-input"
                  value={maxTax}
                  onChange={(e) => setMaxTax(parseFloat(e.target.value) || 0)}
                  step="0.1"
                  min="0"
                />
                <span className="tax-unit">min</span>
              </div>
            </div>

            <div className="policy-card">
              <div className="policy-info">
                <div className="policy-title">
                  <ShieldCheckIcon size={18} color="#00f5a0" />
                  <span>Autonomous PII Redaction Shell</span>
                </div>
                <div className="policy-desc">
                  Real-time pattern scrubbing for emails, SSNs, payment credentials, and confidential auth tokens before persistence.
                </div>
              </div>
              <label className="cyber-switch">
                <input
                  type="checkbox"
                  checked={piiEnabled}
                  onChange={(e) => setPiiEnabled(e.target.checked)}
                />
                <span className="switch-slider" />
              </label>
            </div>

            <div className="policy-card">
              <div className="policy-info">
                <div className="policy-title">
                  <AlertTriangleIcon size={18} color="#f59e0b" />
                  <span>Strict Enforcement Mode (Halt on Breach)</span>
                </div>
                <div className="policy-desc">
                  When enabled, any execution violating safety tax budgets or compliance guardrails will be halted immediately.
                </div>
              </div>
              <label className="cyber-switch">
                <input
                  type="checkbox"
                  checked={strictMode}
                  onChange={(e) => setStrictMode(e.target.checked)}
                />
                <span className="switch-slider" />
              </label>
            </div>
          </div>

          {policyMessage && (
            <div className={`policy-toast ${policyMessage.includes('Failed') ? 'error' : 'success'}`}>
              {policyMessage.includes('Failed') ? <AlertTriangleIcon size={16} /> : <CheckIcon size={16} />}
              <span>{policyMessage}</span>
            </div>
          )}

          <button
            className="policy-save-btn"
            onClick={handleSavePolicy}
            disabled={savingPolicy}
          >
            <ShieldCheckIcon size={18} />
            <span>{savingPolicy ? 'Persisting Safeguards…' : 'Save Policy Configuration'}</span>
          </button>
        </div>
      )}

      {/* WORKSPACES TAB */}
      {activeTab === 'workspaces' && (
        <div className="workspaces-view">
          <div className="workspaces-header">
            <div>
              <h2>Multi-Tenant Workspaces (RBAC)</h2>
              <p>Manage enterprise organizations, tenant environments, cryptographic API keys, and credential roles.</p>
            </div>
            <button className="provision-open-btn" onClick={() => setShowModal(true)}>
              <PlusIcon size={16} />
              <span>Provision Workspace</span>
            </button>
          </div>

          <div className="cyber-table-wrap">
            <table className="cyber-table">
              <thead>
                <tr>
                  <th>Organization</th>
                  <th>Role</th>
                  <th>API Key Reference</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {workspaces.map((w) => (
                  <tr key={w.id}>
                    <td className="org-name-cell">
                      <LayersIcon size={18} color="#00d9ff" />
                      <span>{w.name}</span>
                    </td>
                    <td>
                      <span className="role-badge">{w.role}</span>
                    </td>
                    <td>
                      <span className="api-key-chip">
                        <code>{w.key}</code>
                      </span>
                    </td>
                    <td>
                      <span className="status-active-pill">
                        <div className="live-indicator-dot" />
                        <span>{w.status}</span>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Provision Modal */}
          {showModal && (
            <div className="modal-backdrop">
              <div className="modal-dialog">
                <h3>Provision Organization Workspace</h3>
                <p className="modal-subtitle">Configure an isolated enterprise environment with dedicated API keys and policy shells.</p>

                {createdKey ? (
                  <div>
                    <div className="key-reveal-card">
                      <p style={{ color: '#00f5a0', fontSize: '0.85rem', fontWeight: 700 }}>
                        Workspace provisioned! Store this secret API key safely:
                      </p>
                      <div className="key-reveal-value">{createdKey}</div>
                      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
                        <button
                          className="provision-open-btn"
                          style={{ padding: '0.5rem 1rem', fontSize: '0.82rem' }}
                          onClick={() => copyToClipboard(createdKey, true)}
                        >
                          {copiedKey ? <CheckIcon size={14} /> : <CopyIcon size={14} />}
                          <span>{copiedKey ? 'Copied to Clipboard!' : 'Copy Secret Key'}</span>
                        </button>
                      </div>
                    </div>
                    <div className="modal-actions">
                      <button
                        className="btn-secondary"
                        onClick={() => {
                          setShowModal(false);
                          setCreatedKey(null);
                        }}
                      >
                        Dismiss
                      </button>
                    </div>
                  </div>
                ) : (
                  <form onSubmit={handleProvisionWorkspace}>
                    <div className="modal-field">
                      <label>Organization Legal Entity</label>
                      <input
                        type="text"
                        placeholder="e.g. Acme FinTech Corp"
                        value={newOrgName}
                        onChange={(e) => setNewOrgName(e.target.value)}
                        required
                      />
                    </div>
                    <div className="modal-field">
                      <label>Subscription Tier</label>
                      <select
                        value={newOrgTier}
                        onChange={(e) => setNewOrgTier(e.target.value)}
                      >
                        <option value="community">Community (Sandbox)</option>
                        <option value="team">Team Tier ($99/mo)</option>
                        <option value="business">Business Enterprise ($499/mo)</option>
                        <option value="enterprise">Mission-Critical Custom (SLA)</option>
                      </select>
                    </div>
                    <div className="modal-actions">
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => setShowModal(false)}
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className="provision-open-btn"
                        disabled={provisioning}
                      >
                        <span>{provisioning ? 'Provisioning…' : 'Deploy Environment'}</span>
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

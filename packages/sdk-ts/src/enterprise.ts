export type APVADecision = 'scale' | 'controlled_pilot' | 'optimize' | 'do_not_scale';

export interface APVAGateCheck {
  check: string;
  label: string;
  passed: boolean;
  actual: number | null;
  operator: string;
  threshold: number;
  unit: string;
}

export interface APVABusinessCaseReport {
  report_id: string;
  decision: APVADecision;
  priority_score: number;
  first_year_net_value_usd: number;
  recurring_annual_net_value_usd: number;
  net_present_value_usd: number;
  first_year_roi_pct: number | null;
  payback_months: number | null;
  positive_scenario_rate: number | null;
  gate_checks: APVAGateCheck[];
  [key: string]: unknown;
}

export class APVAWorkflowGateError extends Error {
  public readonly report: APVABusinessCaseReport;

  constructor(report: APVABusinessCaseReport, allowed: readonly APVADecision[]) {
    const failed = report.gate_checks.filter(check => !check.passed).map(check => check.label);
    super(
      `APVA workflow gate rejected '${report.decision}'; allowed: ${allowed.join(', ')}` +
      (failed.length ? `; failed gates: ${failed.join(', ')}` : '')
    );
    this.name = 'APVAWorkflowGateError';
    this.report = report;
  }
}

export class APVAEnterpriseClient {
  private readonly apiUrl: string;
  private readonly apiKey?: string;

  constructor(options?: { apiUrl?: string; apiKey?: string }) {
    const env = (globalThis as any).process?.env;
    this.apiUrl = (options?.apiUrl || env?.APVA_API_URL || 'http://localhost:8000/api/v1').replace(/\/$/, '');
    this.apiKey = options?.apiKey || env?.APVA_API_KEY;
  }

  public analyzeBusinessCase(payload: Record<string, unknown>): Promise<APVABusinessCaseReport> {
    return this.request<APVABusinessCaseReport>('analysis/business-case', 'POST', payload);
  }

  public analyzeObservedBusinessCase(payload: Record<string, unknown>): Promise<APVABusinessCaseReport> {
    return this.request<APVABusinessCaseReport>('analysis/observed-business-case', 'POST', payload);
  }

  public analyzePortfolio(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.request<Record<string, unknown>>('analysis/portfolio', 'POST', payload);
  }

  public policyTemplate(): Promise<Record<string, unknown>> {
    return this.request<Record<string, unknown>>('analysis/policy-template', 'GET');
  }

  public requireDecision(
    report: APVABusinessCaseReport,
    allowed: readonly APVADecision[] = ['scale'],
  ): APVABusinessCaseReport {
    if (!allowed.includes(report.decision)) {
      throw new APVAWorkflowGateError(report, allowed);
    }
    return report;
  }

  public async analyzeAndGate(
    payload: Record<string, unknown>,
    allowed: readonly APVADecision[] = ['scale'],
  ): Promise<APVABusinessCaseReport> {
    return this.requireDecision(await this.analyzeBusinessCase(payload), allowed);
  }

  private async request<T>(path: string, method: 'GET' | 'POST', payload?: Record<string, unknown>): Promise<T> {
    const headers: Record<string, string> = { Accept: 'application/json' };
    if (payload) headers['Content-Type'] = 'application/json';
    if (this.apiKey) headers.Authorization = `Bearer ${this.apiKey}`;
    const fetchFn = (globalThis as any).fetch;
    if (typeof fetchFn !== 'function') throw new Error('APVA SDK requires a global fetch implementation');
    const response = await fetchFn(`${this.apiUrl}/${path}`, {
      method,
      headers,
      body: payload ? JSON.stringify(payload) : undefined,
    });
    if (!response.ok) throw new Error(`APVA analysis HTTP error: ${response.status}`);
    return response.json() as Promise<T>;
  }
}

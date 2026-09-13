export interface TelemetryEventPayload {
  app_name: string;
  session_id: string;
  run_id: string;
  human_baseline_time: number;
  ai_augmented_time: number;
  guardrail_latency_tax: number;
  session_iterations?: number;
  hourly_rate_usd?: number;
  is_shadow?: boolean;
  metadata?: Record<string, any>;
}

export interface DeliveryStats {
  accepted: number;
  dropped: number;
  sent: number;
  failed: number;
  batches: number;
}

export function generateUUID(): string {
  if (typeof globalThis !== 'undefined' && (globalThis as any).crypto?.randomUUID) {
    return (globalThis as any).crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export class APVATelemetryClient {
  private endpoint: string;
  private apiKey?: string;
  public appName: string;
  public sessionId: string;
  private queue: TelemetryEventPayload[] = [];
  private maxQueueSize: number;
  private isFlushing: boolean = false;
  private intervalId?: any;
  private maxRetries: number;
  private batchSize: number;
  private deliveryStats: DeliveryStats = { accepted: 0, dropped: 0, sent: 0, failed: 0, batches: 0 };

  constructor(options?: {
    endpoint?: string;
    apiKey?: string;
    appName?: string;
    sessionId?: string;
    queueSize?: number;
    maxRetries?: number;
    batchSize?: number;
  }) {
    const envEndpoint = (globalThis as any).process?.env?.APVA_INGEST_URL;
    this.endpoint = options?.endpoint || envEndpoint || 'http://localhost:8000/api/v1/telemetry/ingest';
    this.apiKey = options?.apiKey;
    this.appName = options?.appName || 'apva-sdk-ts';
    this.sessionId = options?.sessionId || generateUUID().replace(/-/g, '');
    this.maxQueueSize = options?.queueSize || 2000;
    this.maxRetries = options?.maxRetries || 3;
    this.batchSize = options?.batchSize || 50;

    // Background flusher loop every 200ms
    this.intervalId = setInterval(() => this.flush(), 200);
    if (this.intervalId && typeof (this.intervalId as any).unref === 'function') {
      (this.intervalId as any).unref();
    }
  }

  public ingestAsync(payload: TelemetryEventPayload): boolean {
    if (this.queue.length >= this.maxQueueSize) {
      this.deliveryStats.dropped++;
      return false; // Queue full
    }
    this.queue.push(payload);
    this.deliveryStats.accepted++;
    return true;
  }

  public async ingest(payload: TelemetryEventPayload): Promise<void> {
    await this.send(payload);
  }

  public ingestBatch(payloads: TelemetryEventPayload[]): number {
    let enqueued = 0;
    for (const p of payloads) {
      if (this.ingestAsync(p)) {
        enqueued++;
      }
    }
    return enqueued;
  }

  public getStats(): Readonly<DeliveryStats> {
    return { ...this.deliveryStats };
  }

  public async close(timeoutMs: number = 2000): Promise<void> {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
    const start = Date.now();
    while (this.queue.length > 0 && Date.now() - start < timeoutMs) {
      await this.flush();
      await new Promise(resolve => setTimeout(resolve, 50));
    }
  }

  private async flush(): Promise<void> {
    if (this.isFlushing || this.queue.length === 0) {
      return;
    }
    this.isFlushing = true;
    try {
      while (this.queue.length > 0) {
        const batch = this.queue.splice(0, this.batchSize);
        try {
          await this.sendWithRetry(batch);
          this.deliveryStats.sent += batch.length;
        } catch (error) {
          this.deliveryStats.failed += batch.length;
          // Drop on permanent failure to prevent queue buildup.
        }
        this.deliveryStats.batches++;
      }
    } finally {
      this.isFlushing = false;
    }
  }

  private async sendWithRetry(payloads: TelemetryEventPayload[]): Promise<void> {
    for (let attempt = 0; attempt < this.maxRetries; attempt++) {
      try {
        await this.sendBatchRequest(payloads);
        return;
      } catch (error) {
        if (attempt === this.maxRetries - 1) {
          throw error;
        }
        const delay = Math.min(100 * Math.pow(2, attempt), 2000);
        await new Promise(res => setTimeout(res, delay));
      }
    }
  }

  private async send(payload: TelemetryEventPayload): Promise<void> {
    await this.sendBatchRequest([payload]);
  }

  private async sendBatchRequest(payloads: TelemetryEventPayload[]): Promise<void> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }

    const normalized = payloads.map(payload => ({
        ...payload,
        session_iterations: payload.session_iterations ?? 1,
        hourly_rate_usd: payload.hourly_rate_usd ?? null,
        is_shadow: payload.is_shadow ?? false,
        metadata: payload.metadata ?? {},
      }));
    const isBatch = normalized.length > 1;
    const body = JSON.stringify(isBatch ? { events: normalized } : normalized[0]);
    const endpoint = isBatch ? `${this.endpoint.replace(/\/$/, '')}/batch` : this.endpoint;

    const fetchFn = (globalThis as any).fetch;
    if (typeof fetchFn === 'function') {
      const res = await fetchFn(endpoint, {
        method: 'POST',
        headers,
        body,
      });
      if (!res.ok) {
        throw new Error(`APVA ingest HTTP error: ${res.status}`);
      }
    }
  }
}

let _defaultClient: APVATelemetryClient | null = null;

export function getDefaultClient(): APVATelemetryClient {
  if (!_defaultClient) {
    _defaultClient = new APVATelemetryClient();
  }
  return _defaultClient;
}

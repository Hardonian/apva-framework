import axios, { AxiosInstance } from 'axios';
import { randomUUID } from 'crypto';

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

export class APVATelemetryClient {
  private endpoint: string;
  private apiKey?: string;
  public appName: string;
  public sessionId: string;
  private queue: TelemetryEventPayload[] = [];
  private maxQueueSize: number;
  private isFlushing: boolean = false;
  private httpClient: AxiosInstance;
  private intervalId?: NodeJS.Timeout;

  constructor(options?: {
    endpoint?: string;
    apiKey?: string;
    appName?: string;
    sessionId?: string;
    queueSize?: number;
  }) {
    this.endpoint = options?.endpoint || process.env.APVA_INGEST_URL || 'http://localhost:8000/api/v1/telemetry/ingest';
    this.apiKey = options?.apiKey;
    this.appName = options?.appName || 'apva-sdk-ts';
    this.sessionId = options?.sessionId || randomUUID().replace(/-/g, '');
    this.maxQueueSize = options?.queueSize || 1000;
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }
    
    // Create an axios instance with HTTP Keep-Alive
    this.httpClient = axios.create({
      timeout: 5000,
      headers
    });

    // Start background flusher loop every 200ms
    this.intervalId = setInterval(() => this.flush(), 200);
    // Ensure the interval doesn't keep the Node.js process alive if it's the only thing left
    if (this.intervalId.unref) {
        this.intervalId.unref();
    }
  }

  public ingestAsync(payload: TelemetryEventPayload): boolean {
    if (this.queue.length >= this.maxQueueSize) {
      return false; // Queue full
    }
    this.queue.push(payload);
    return true;
  }

  public async ingest(payload: TelemetryEventPayload): Promise<void> {
    await this.send(payload);
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
        const payload = this.queue.shift();
        if (payload) {
          try {
            await this.send(payload);
          } catch (error) {
            // Drop on error to prevent queue buildup
          }
        }
      }
    } finally {
      this.isFlushing = false;
    }
  }

  private async send(payload: TelemetryEventPayload): Promise<void> {
    await this.httpClient.post(this.endpoint, {
      ...payload,
      session_iterations: payload.session_iterations ?? 1,
      hourly_rate_usd: payload.hourly_rate_usd ?? null,
      is_shadow: payload.is_shadow ?? false,
      metadata: payload.metadata ?? {}
    });
  }
}

let _defaultClient: APVATelemetryClient | null = null;

export function getDefaultClient(): APVATelemetryClient {
  if (!_defaultClient) {
    _defaultClient = new APVATelemetryClient();
  }
  return _defaultClient;
}

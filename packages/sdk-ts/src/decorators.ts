import { APVATelemetryClient, TelemetryEventPayload, getDefaultClient } from './client';
import { randomUUID } from 'crypto';

export interface TrackerOptions {
  client?: APVATelemetryClient;
  appName?: string;
  sessionId?: string;
  runId?: string;
  humanBaselineTime?: number;
  hourlyRateUsd?: number;
  isShadow?: boolean;
  metadata?: Record<string, any>;
}

export interface GuardrailOptions extends TrackerOptions {
  aiAugmentedTime?: number;
  sessionIterations?: number;
}

export function ApvaTrackLatency(options?: TrackerOptions) {
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value;

    descriptor.value = async function (...args: any[]) {
      const client = options?.client || getDefaultClient();
      const appName = options?.appName || client.appName;
      const sessionId = options?.sessionId || client.sessionId;
      const runId = options?.runId || randomUUID().replace(/-/g, '');
      const metadata = options?.metadata || {};

      const start = performance.now();
      const result = await originalMethod.apply(this, args);
      const elapsedMin = (performance.now() - start) / 60000.0;

      const payload: TelemetryEventPayload = {
        app_name: appName,
        session_id: sessionId,
        run_id: runId,
        human_baseline_time: options?.humanBaselineTime || 0.0,
        ai_augmented_time: elapsedMin,
        guardrail_latency_tax: 0.0,
        session_iterations: 1,
        hourly_rate_usd: options?.hourlyRateUsd,
        is_shadow: options?.isShadow || false,
        metadata: { ...metadata }
      };

      client.ingestAsync(payload);
      return result;
    };
    return descriptor;
  };
}

export function ApvaGuardrailCheck(options?: GuardrailOptions) {
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value;

    descriptor.value = async function (...args: any[]) {
      const client = options?.client || getDefaultClient();
      const appName = options?.appName || client.appName;
      const sessionId = options?.sessionId || client.sessionId;
      const runId = options?.runId || randomUUID().replace(/-/g, '');
      const metadata = options?.metadata || {};

      const start = performance.now();
      const result = await originalMethod.apply(this, args);
      const elapsedMin = (performance.now() - start) / 60000.0;

      const payload: TelemetryEventPayload = {
        app_name: appName,
        session_id: sessionId,
        run_id: runId,
        human_baseline_time: options?.humanBaselineTime || 0.0,
        ai_augmented_time: options?.aiAugmentedTime || 0.0,
        guardrail_latency_tax: elapsedMin,
        session_iterations: options?.sessionIterations || 1,
        hourly_rate_usd: options?.hourlyRateUsd,
        is_shadow: options?.isShadow || false,
        metadata: { ...metadata }
      };

      client.ingestAsync(payload);
      return result;
    };
    return descriptor;
  };
}

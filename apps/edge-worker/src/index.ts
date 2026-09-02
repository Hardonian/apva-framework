/**
 * APVA Global Edge Ingestion Network (Cloudflare Worker)
 *
 * Deployed across 300+ data centers worldwide.
 * Ingests single and batch telemetry payloads with <10ms edge response,
 * enforces PII redaction at the edge, and streams to Kafka/Backend asynchronously.
 */

export interface Env {
	KAFKA_REST_PROXY_URL?: string;
	APVA_KAFKA_TOPIC?: string;
	BACKEND_INGEST_URL?: string;
}

export interface ExecutionContext {
	waitUntil(promise: Promise<any>): void;
	passThroughOnException?(): void;
}

const CORS_HEADERS = {
	'Access-Control-Allow-Origin': '*',
	'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
	'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Request-ID, X-APVA-Version',
};

// Edge PII redaction patterns
const EMAIL_REGEX = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
const SSN_REGEX = /\b\d{3}-\d{2}-\d{4}\b/g;
const KEY_REGEX = /\b(?:sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|apva_[a-zA-Z0-9_-]{20,})\b/g;

function sanitizePII(value: any): any {
	if (typeof value === 'string') {
		return value
			.replace(EMAIL_REGEX, '[EMAIL_REDACTED]')
			.replace(SSN_REGEX, '[SSN_REDACTED]')
			.replace(KEY_REGEX, '[KEY_REDACTED]');
	}
	if (Array.isArray(value)) {
		return value.map(sanitizePII);
	}
	if (value !== null && typeof value === 'object') {
		const out: Record<string, any> = {};
		for (const k of Object.keys(value)) {
			out[k] = sanitizePII(value[k]);
		}
		return out;
	}
	return value;
}

export default {
	async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
		if (request.method === 'OPTIONS') {
			return new Response(null, { headers: CORS_HEADERS });
		}

		const url = new URL(request.url);

		if (request.method === 'GET' && (url.pathname === '/' || url.pathname === '/health' || url.pathname === '/api/v1/health')) {
			return new Response(JSON.stringify({
				status: 'ok',
				service: 'apva-edge-worker',
				version: '3.0.0',
				colo: (request as any).cf?.colo || 'LOCAL',
			}), {
				status: 200,
				headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
			});
		}

		if (request.method !== 'POST') {
			return new Response(JSON.stringify({ error: 'Method Not Allowed' }), {
				status: 405,
				headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
			});
		}

		try {
			const body = await request.json() as any;
			const authHeader = request.headers.get('Authorization') || 'Bearer anon';

			// Batch endpoint: /api/v1/telemetry/ingest/batch
			if (url.pathname.includes('/batch')) {
				const events = Array.isArray(body) ? body : (body.events || []);
				if (!Array.isArray(events) || events.length === 0) {
					return new Response(JSON.stringify({ error: 'Expected non-empty array of events' }), {
						status: 422,
						headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
					});
				}

				const sanitizedEvents = events.map(sanitizePII);
				ctx.waitUntil(dispatchPayload(env, { events: sanitizedEvents }, authHeader));

				return new Response(JSON.stringify({
					status: 'accepted',
					edge_buffered: true,
					batch_size: events.length,
				}), {
					status: 202,
					headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
				});
			}

			// Single event ingest
			const payload = body as Record<string, any>;
			if (!payload.app_name || !payload.session_id || !payload.run_id) {
				return new Response(JSON.stringify({ error: 'Missing required fields: app_name, session_id, run_id' }), {
					status: 422,
					headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
				});
			}

			const sanitizedPayload = sanitizePII(payload);
			ctx.waitUntil(dispatchPayload(env, sanitizedPayload, authHeader));

			return new Response(JSON.stringify({
				status: 'accepted',
				edge_buffered: true,
				event_id: payload.run_id,
			}), {
				status: 202,
				headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
			});
		} catch {
			return new Response(JSON.stringify({ error: 'Bad Request' }), {
				status: 400,
				headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
			});
		}
	},
};

async function dispatchPayload(env: Env, payload: any, token: string) {
	// 1. Publish to Kafka REST proxy if configured
	if (env.KAFKA_REST_PROXY_URL) {
		try {
			await fetch(env.KAFKA_REST_PROXY_URL, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/vnd.kafka.json.v2+json',
					Authorization: token,
				},
				body: JSON.stringify({ records: [{ value: payload }] }),
			});
		} catch (err) {
			console.error('[EDGE] Kafka publish error:', err);
		}
	}

	// 2. Direct backend forward if configured
	if (env.BACKEND_INGEST_URL) {
		try {
			const isBatch = Array.isArray(payload.events);
			const url = isBatch
				? `${env.BACKEND_INGEST_URL.replace(/\/+$/, '')}/batch`
				: env.BACKEND_INGEST_URL;
			await fetch(url, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: token,
				},
				body: JSON.stringify(payload),
			});
		} catch (err) {
			console.error('[EDGE] Backend forward error:', err);
		}
	}
}

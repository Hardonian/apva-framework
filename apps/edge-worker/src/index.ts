/**
 * APVA Global Edge Ingestion Network (Cloudflare Worker)
 *
 * Deployed to 300+ data centers globally. Accepts telemetry payloads with
 * <10ms latency and buffers them into Kafka topics, protecting the core
 * backend database from traffic spikes.
 */

export interface Env {
	KAFKA_REST_PROXY_URL: string;
	APVA_KAFKA_TOPIC: string;
}

const CORS_HEADERS = {
	'Access-Control-Allow-Origin': '*',
	'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
	'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Request-ID',
};

export default {
	async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
		if (request.method === 'OPTIONS') {
			return new Response(null, { headers: CORS_HEADERS });
		}

		const url = new URL(request.url);

		if (request.method === 'GET' && (url.pathname === '/' || url.pathname === '/health' || url.pathname === '/api/v1/health')) {
			return new Response(JSON.stringify({ status: 'ok', service: 'apva-edge-worker', version: '2.1.0' }), {
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
			const payload = await request.json() as Record<string, any>;

			// Validate payload basics
			if (!payload.app_name || !payload.session_id || !payload.run_id) {
				return new Response(JSON.stringify({ error: 'Missing required fields: app_name, session_id, run_id' }), {
					status: 422,
					headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
				});
			}

			// Extract tenant info from Authorization header (JWT)
			const authHeader = request.headers.get('Authorization') || 'Bearer anon';

			// Buffer to Kafka without blocking client response
			ctx.waitUntil(publishToKafka(env, payload, authHeader));

			// Immediately return 202 Accepted to the client (<10ms latency)
			return new Response(JSON.stringify({ status: 'accepted', edge_buffered: true, event_id: payload.run_id }), {
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

async function publishToKafka(env: Env, payload: any, token: string) {
	console.log(`[EDGE] Buffering payload ${payload?.run_id} to Kafka topic ${env.APVA_KAFKA_TOPIC || 'apva-telemetry'}`);
	if (env.KAFKA_REST_PROXY_URL) {
		try {
			await fetch(env.KAFKA_REST_PROXY_URL, {
				method: 'POST',
				headers: { 'Content-Type': 'application/vnd.kafka.json.v2+json', Authorization: token },
				body: JSON.stringify({ records: [{ value: payload }] }),
			});
		} catch (err) {
			console.error('[EDGE] Kafka publish error:', err);
		}
	}
}

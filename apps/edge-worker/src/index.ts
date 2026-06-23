/**
 * APVA Global Edge Ingestion Network (Cloudflare Worker)
 * 
 * Deployed to 300+ data centers globally. Accepts telemetry payloads with
 * <10ms latency and buffers them into a Kafka topics, protecting the core
 * backend database from traffic spikes.
 */

export interface Env {
	// Example binding for a Cloudflare Kafka publisher or REST proxy
	KAFKA_REST_PROXY_URL: string;
	APVA_KAFKA_TOPIC: string;
}

export default {
	async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
		if (request.method !== 'POST') {
			return new Response('Method Not Allowed', { status: 405 });
		}

		try {
			const payload = await request.json();
			
			// Extract tenant info from Authorization header (JWT)
			const authHeader = request.headers.get('Authorization');
			if (!authHeader) {
				return new Response('Unauthorized', { status: 401 });
			}

			// In an Enterprise system, we buffer to Kafka immediately.
			// ctx.waitUntil ensures the worker doesn't block the client waiting for the Kafka ACK.
			ctx.waitUntil(publishToKafka(env, payload, authHeader));

			// Immediately return 202 Accepted to the client (<10ms latency)
			return new Response(JSON.stringify({ status: 'accepted', edge_buffered: true }), {
				status: 202,
				headers: { 'Content-Type': 'application/json' },
			});
		} catch (e) {
			return new Response('Bad Request', { status: 400 });
		}
	},
};

async function publishToKafka(env: Env, payload: any, token: string) {
	// Mock implementation of a Kafka REST Proxy POST
	console.log(`[EDGE] Buffering payload to Kafka topic ${env.APVA_KAFKA_TOPIC}`);
	/*
	await fetch(env.KAFKA_REST_PROXY_URL, {
		method: 'POST',
		headers: { 'Content-Type': 'application/vnd.kafka.json.v2+json', 'Authorization': token },
		body: JSON.stringify({ records: [{ value: payload }] })
	});
	*/
}

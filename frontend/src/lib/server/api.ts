import { env } from '$env/dynamic/private';

/** SSR-side API client — uses INTERNAL_API_URL for Docker-internal communication */
export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
	const controller = new AbortController();
	const timeout = setTimeout(() => controller.abort(), 10_000);
	try {
		const res = await fetch(`${env.INTERNAL_API_URL}${path}`, {
			...init,
			signal: controller.signal,
			headers: { 'Content-Type': 'application/json', ...init?.headers }
		});
		if (!res.ok) throw new Error(`API error: ${res.status}`);
		return res;
	} finally {
		clearTimeout(timeout);
	}
}

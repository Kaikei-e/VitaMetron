/** Browser-side API client — uses relative paths (Nginx routes to Go API) */
export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
	const res = await fetch(path, {
		...init,
		headers: { 'Content-Type': 'application/json', ...init?.headers }
	});
	if (!res.ok) throw new Error(`API error: ${res.status}`);
	return res;
}

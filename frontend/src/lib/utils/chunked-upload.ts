export interface ChunkUploadOptions {
	file: File;
	initUrl: string;
	chunkUrl: (uploadId: string, index: number) => string;
	completeUrl: (uploadId: string) => string;
	chunkSize?: number;
	onProgress?: (percent: number) => void;
}

const DEFAULT_CHUNK_SIZE = 80 * 1024 * 1024; // 80MB — under Cloudflare Tunnel 100MB limit

export async function chunkedUpload(opts: ChunkUploadOptions): Promise<string> {
	const chunkSize = opts.chunkSize ?? DEFAULT_CHUNK_SIZE;
	const totalChunks = Math.ceil(opts.file.size / chunkSize);

	// 1. Init upload session
	const initRes = await fetch(opts.initUrl, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			file_name: opts.file.name,
			file_size: opts.file.size,
			chunk_size: chunkSize
		})
	});
	if (!initRes.ok) {
		let errMsg = `Failed to init upload (HTTP ${initRes.status})`;
		try {
			const err = await initRes.json();
			errMsg = err.error || errMsg;
		} catch {
			// non-JSON response (e.g. nginx error page)
		}
		throw new Error(errMsg);
	}
	const { upload_id } = await initRes.json();

	// 2. Upload chunks sequentially
	for (let i = 0; i < totalChunks; i++) {
		const start = i * chunkSize;
		const end = Math.min(start + chunkSize, opts.file.size);
		const chunk = opts.file.slice(start, end);

		const res = await fetch(opts.chunkUrl(upload_id, i), {
			method: 'PUT',
			headers: { 'Content-Type': 'application/octet-stream' },
			body: chunk
		});
		if (!res.ok) {
			let errMsg = `Chunk ${i} upload failed (HTTP ${res.status})`;
			try {
				const err = await res.json();
				errMsg = err.error || errMsg;
			} catch {
				// non-JSON response (e.g. nginx 413 error page)
			}
			throw new Error(errMsg);
		}

		opts.onProgress?.(Math.round(((i + 1) / totalChunks) * 100));
	}

	// 3. Complete upload
	const completeRes = await fetch(opts.completeUrl(upload_id), { method: 'POST' });
	if (!completeRes.ok) {
		let errMsg = `Failed to complete upload (HTTP ${completeRes.status})`;
		try {
			const err = await completeRes.json();
			errMsg = err.error || errMsg;
		} catch {
			// non-JSON response (e.g. nginx error page)
		}
		throw new Error(errMsg);
	}
	const { job_id } = await completeRes.json();
	return job_id;
}

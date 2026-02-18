export interface StreamProgressOptions<T> {
	streamUrl: string;
	statusUrl: string;
	onProgress: (data: T) => void;
	isCompleted: (data: T) => boolean;
	isFailed: (data: T) => boolean;
	getError: (data: T) => string;
	getResult: (data: T) => unknown;
}

export function streamProgress<T>(opts: StreamProgressOptions<T>): Promise<unknown> {
	return new Promise((resolve, reject) => {
		const es = new EventSource(opts.streamUrl);

		es.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data) as T;
				opts.onProgress(data);

				if (opts.isCompleted(data)) {
					es.close();
					resolve(opts.getResult(data));
				} else if (opts.isFailed(data)) {
					es.close();
					reject(new Error(opts.getError(data)));
				}
			} catch {
				// ignore parse errors
			}
		};

		es.onerror = () => {
			es.close();
			// Fallback: try to get final status via polling
			fetch(opts.statusUrl)
				.then((r) => r.json())
				.then((data: T) => {
					if (opts.isCompleted(data)) {
						resolve(opts.getResult(data));
					} else {
						reject(new Error('Connection lost during processing'));
					}
				})
				.catch(() => reject(new Error('Connection lost during processing')));
		};
	});
}

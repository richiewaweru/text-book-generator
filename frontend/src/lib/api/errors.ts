export class ApiError extends Error {
	status: number;
	detail: string;
	errorType: string | null;

	constructor(status: number, detail: string, errorType: string | null = null) {
		super(detail);
		this.name = 'ApiError';
		this.status = status;
		this.detail = detail;
		this.errorType = errorType;
	}
}

interface ApiErrorPayload {
	detail?: string;
	error_type?: string;
}

function isObject(value: unknown): value is Record<string, unknown> {
	return typeof value === 'object' && value !== null;
}

async function readErrorPayload(response: Response): Promise<ApiErrorPayload | null> {
	const contentType = response.headers.get('content-type') ?? '';

	if (contentType.includes('application/json')) {
		try {
			const payload = (await response.json()) as unknown;
			if (isObject(payload)) {
				return {
					detail: typeof payload.detail === 'string' ? payload.detail : undefined,
					error_type: typeof payload.error_type === 'string' ? payload.error_type : undefined
				};
			}
		} catch {
			return null;
		}
		return null;
	}

	try {
		const text = (await response.text()).trim();
		return text ? { detail: text } : null;
	} catch {
		return null;
	}
}

export async function ensureOk(response: Response, fallbackMessage: string): Promise<Response> {
	if (response.ok) {
		return response;
	}

	const payload = await readErrorPayload(response);
	throw new ApiError(
		response.status,
		payload?.detail ?? (response.statusText || fallbackMessage),
		payload?.error_type ?? null
	);
}

export function isApiError(error: unknown): error is ApiError {
	return error instanceof ApiError;
}

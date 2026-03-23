export interface ApiEnvironment {
	PUBLIC_API_URL?: string;
	VITE_API_TARGET?: string;
}

function pickConfiguredUrl(...values: Array<string | undefined>): string | undefined {
	return values.find((value) => value?.trim().length);
}

function normalizeUrl(value: string | undefined): string {
	return (value ?? '').trim().replace(/\/$/, '');
}

export function resolveClientApiBase(env: ApiEnvironment): string {
	return normalizeUrl(pickConfiguredUrl(env.PUBLIC_API_URL, env.VITE_API_TARGET));
}

export function resolveDevProxyTarget(
	env: ApiEnvironment,
	fallback = 'http://localhost:8000'
): string {
	return normalizeUrl(pickConfiguredUrl(env.VITE_API_TARGET, env.PUBLIC_API_URL, fallback));
}

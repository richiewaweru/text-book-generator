export interface FrontendEnvironment {
	PUBLIC_API_URL?: string;
	VITE_API_TARGET?: string;
	VITE_GOOGLE_CLIENT_ID?: string;
}

function pickConfiguredUrl(...values: Array<string | undefined>): string | undefined {
	return values.find((value) => value?.trim().length);
}

function normalizeUrl(value: string | undefined): string {
	return (value ?? '').trim().replace(/\/$/, '');
}

function isDockerFrontendHost(locationLike?: Pick<Location, 'port'> | null): boolean {
	const source =
		locationLike ?? (typeof window !== 'undefined' ? window.location : null);

	if (!source) {
		return false;
	}

	return source.port === '3000';
}

export function resolveClientApiBase(env: FrontendEnvironment): string {
	return normalizeUrl(pickConfiguredUrl(env.PUBLIC_API_URL, env.VITE_API_TARGET));
}

export function resolveDevProxyTarget(
	env: FrontendEnvironment,
	fallback = 'http://localhost:8000'
): string {
	return normalizeUrl(pickConfiguredUrl(env.VITE_API_TARGET, env.PUBLIC_API_URL, fallback));
}

export function resolveGoogleClientId(env: FrontendEnvironment): string {
	return (env.VITE_GOOGLE_CLIENT_ID ?? '').trim();
}

export function googleClientIdMissingMessage(locationLike?: Pick<Location, 'port'> | null): string {
	if (isDockerFrontendHost(locationLike)) {
		return 'Google sign-in is unavailable because VITE_GOOGLE_CLIENT_ID is missing. Set GOOGLE_CLIENT_ID in the repo-root .env.';
	}

	return 'Google sign-in is unavailable because VITE_GOOGLE_CLIENT_ID is missing. Set VITE_GOOGLE_CLIENT_ID in frontend/.env.';
}

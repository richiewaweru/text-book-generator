import type { AuthResponse, User } from '$lib/types';
import { apiFetch } from './client';

export async function exchangeGoogleToken(credential: string): Promise<AuthResponse> {
	const response = await apiFetch('/api/v1/auth/google', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ credential })
	});

	if (!response.ok) {
		throw new Error(`Authentication failed: ${response.statusText}`);
	}

	return response.json();
}

export async function fetchCurrentUser(): Promise<User> {
	const response = await apiFetch('/api/v1/auth/me');

	if (!response.ok) {
		throw new Error(`Failed to fetch user: ${response.statusText}`);
	}

	return response.json();
}

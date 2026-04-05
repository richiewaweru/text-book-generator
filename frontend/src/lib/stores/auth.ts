import { derived, get, writable } from 'svelte/store';
import { isApiError } from '$lib/api/errors';
import type { AuthResponse, User } from '$lib/types';

const TOKEN_KEY = 'textbook_agent_token';
const USER_KEY = 'textbook_agent_user';

function hasStorage(): boolean {
	return typeof localStorage !== 'undefined';
}

function safeLoadFromStorage(): { token: string | null; user: User | null } {
	if (!hasStorage()) return { token: null, user: null };

	try {
		const token = localStorage.getItem(TOKEN_KEY);
		const raw = localStorage.getItem(USER_KEY);
		const user = raw ? (JSON.parse(raw) as User) : null;
		return { token, user };
	} catch (error) {
		console.error('Failed to load auth from storage', error);
		try {
			localStorage.removeItem(TOKEN_KEY);
			localStorage.removeItem(USER_KEY);
		} catch {}
		return { token: null, user: null };
	}
}

const tokenStore = writable<string | null>(null);
const userStore = writable<User | null>(null);
const initializedStore = writable(false);

function persistSession(token: string | null, user: User | null) {
	if (!hasStorage()) return;

	try {
		if (token) localStorage.setItem(TOKEN_KEY, token);
		else localStorage.removeItem(TOKEN_KEY);

		if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
		else localStorage.removeItem(USER_KEY);
	} catch (error) {
		console.error('Failed to persist auth session', error);
	}
}

function setSession(token: string | null, user: User | null) {
	tokenStore.set(token);
	userStore.set(user);
	persistSession(token, user);
}

export const authToken = { subscribe: tokenStore.subscribe };
export const authUser = { subscribe: userStore.subscribe };
export const authInitialized = { subscribe: initializedStore.subscribe };

export const authIsAuthenticated = derived(
	[tokenStore, userStore],
	([$token, $user]) => $token !== null && $user !== null
);

export async function bootstrapAuth(resolveCurrentUser: () => Promise<User>): Promise<User | null> {
	try {
		const stored = safeLoadFromStorage();
		tokenStore.set(stored.token);
		userStore.set(stored.user);

		if (!stored.token) {
			setSession(null, null);
			return null;
		}

		try {
			const user = await resolveCurrentUser();
			setSession(stored.token, user);
			return user;
		} catch (error) {
			if (isApiError(error) && error.status === 401) {
				setSession(null, null);
				return null;
			}

			console.error('bootstrapAuth fetchCurrentUser failed', error);
			return stored.user;
		}
	} finally {
		initializedStore.set(true);
	}
}
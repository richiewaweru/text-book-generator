import type { User, AuthResponse } from '$lib/types';

const TOKEN_KEY = 'textbook_agent_token';
const USER_KEY = 'textbook_agent_user';

function loadFromStorage(): { token: string | null; user: User | null } {
	if (typeof window === 'undefined') return { token: null, user: null };
	const token = localStorage.getItem(TOKEN_KEY);
	const raw = localStorage.getItem(USER_KEY);
	const user = raw ? (JSON.parse(raw) as User) : null;
	return { token, user };
}

let _token = $state<string | null>(null);
let _user = $state<User | null>(null);
let _initialized = $state(false);

export function initAuth() {
	const stored = loadFromStorage();
	_token = stored.token;
	_user = stored.user;
	_initialized = true;
}

export function getToken(): string | null {
	return _token;
}

export function getUser(): User | null {
	return _user;
}

export function isAuthenticated(): boolean {
	return _token !== null && _user !== null;
}

export function isInitialized(): boolean {
	return _initialized;
}

export function setAuth(response: AuthResponse) {
	_token = response.access_token;
	_user = response.user;
	localStorage.setItem(TOKEN_KEY, response.access_token);
	localStorage.setItem(USER_KEY, JSON.stringify(response.user));
}

export function updateUser(user: User) {
	_user = user;
	localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function logout() {
	_token = null;
	_user = null;
	localStorage.removeItem(TOKEN_KEY);
	localStorage.removeItem(USER_KEY);
}

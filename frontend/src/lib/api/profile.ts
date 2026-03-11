import type { StudentProfile, ProfileCreateRequest } from '$lib/types';
import { apiFetch } from './client';

export async function getProfile(): Promise<StudentProfile> {
	const response = await apiFetch('/api/v1/profile');

	if (!response.ok) {
		throw new Error(`Failed to fetch profile: ${response.statusText}`);
	}

	return response.json();
}

export async function createProfile(data: ProfileCreateRequest): Promise<StudentProfile> {
	const response = await apiFetch('/api/v1/profile', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});

	if (!response.ok) {
		throw new Error(`Failed to create profile: ${response.statusText}`);
	}

	return response.json();
}

export async function updateProfile(
	data: Partial<ProfileCreateRequest>
): Promise<StudentProfile> {
	const response = await apiFetch('/api/v1/profile', {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(data)
	});

	if (!response.ok) {
		throw new Error(`Failed to update profile: ${response.statusText}`);
	}

	return response.json();
}

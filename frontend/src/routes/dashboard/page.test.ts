// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { authStore } = vi.hoisted(() => {
	let current = {
		id: 'user-1',
		email: 'teacher@example.com',
		name: 'Alex',
		picture_url: null,
		has_profile: true,
		created_at: '2026-04-06T00:00:00Z',
		updated_at: '2026-04-06T00:00:00Z'
	};
	const subscribers = new Set<(value: unknown) => void>();

	return {
		authStore: {
			subscribe(callback: (value: unknown) => void) {
				subscribers.add(callback);
				callback(current);
				return () => subscribers.delete(callback);
			},
			set(value: typeof current) {
				current = value;
				for (const callback of subscribers) {
					callback(current);
				}
			}
		}
	};
});

const { getProfile, getGenerations } = vi.hoisted(() => ({
	getProfile: vi.fn(),
	getGenerations: vi.fn()
}));

vi.mock('lectio', () => ({
	basePresetMap: {},
	templateRegistryMap: {}
}));

vi.mock('$app/navigation', () => ({
	goto: vi.fn()
}));

vi.mock('$lib/api/profile', () => ({
	getProfile
}));

vi.mock('$lib/api/client', () => ({
	getGenerations
}));

vi.mock('$lib/api/errors', () => ({
	isApiError: () => false
}));

vi.mock('$lib/auth/routing', () => ({
	getOnboardingRoute: () => '/onboarding',
	resolveDashboardProfileFailure: () => ({ redirectTo: null, message: null })
}));

vi.mock('$lib/stores/auth', () => ({
	authUser: authStore,
	logout: vi.fn()
}));

vi.mock('$lib/navigation/textbook', () => ({
	getTextbookRoute: (id: string) => `/textbook/${id}`
}));

vi.mock('$lib/generation/error-messages', () => ({
	friendlyGenerationErrorMessage: () => 'Generation failed.'
}));

import DashboardPage from './+page.svelte';

describe('dashboard teacher profile summary', () => {
	beforeEach(() => {
		getProfile.mockResolvedValue({
			id: 'profile-1',
			user_id: 'user-1',
			teacher_role: 'teacher',
			subjects: ['mathematics', 'physics'],
			default_grade_band: 'high_school',
			default_audience_description: 'Year 10 mixed-ability maths',
			curriculum_framework: 'GCSE AQA',
			classroom_context: 'Limited devices, mixed prior knowledge.',
			planning_goals: 'Better first drafts and more scaffolded practice.',
			school_or_org_name: 'Riverside High',
			delivery_preferences: {
				tone: 'supportive',
				reading_level: 'simple',
				explanation_style: 'concrete-first',
				example_style: 'everyday',
				brevity: 'tight',
				use_visuals: true,
				print_first: true,
				more_practice: true,
				keep_short: false
			},
			created_at: '2026-04-06T00:00:00Z',
			updated_at: '2026-04-06T00:00:00Z'
		});
		getGenerations.mockResolvedValue([]);
	});

	afterEach(() => {
		cleanup();
		vi.clearAllMocks();
	});

	it('shows teacher-facing summary fields instead of learner labels', async () => {
		render(DashboardPage);

		await waitFor(() => expect(screen.getByText(/teacher setup/i)).toBeTruthy());

		expect(screen.getByText(/teacher role/i)).toBeTruthy();
		expect(screen.getByText(/default grade band/i)).toBeTruthy();
		expect(screen.getByText(/default audience/i)).toBeTruthy();
		expect(screen.getByText(/curriculum/i)).toBeTruthy();
		expect(screen.getByText(/classroom context/i)).toBeTruthy();
		expect(screen.getByText(/planning goals/i)).toBeTruthy();
		expect(screen.queryByText(/learning style/i)).toBeNull();
		expect(screen.queryByText(/learner description/i)).toBeNull();
	});
});

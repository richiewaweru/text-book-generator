<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { fromStore } from 'svelte/store';
	import ProfileSetup from '$lib/components/ProfileSetup.svelte';
	import { fetchCurrentUser } from '$lib/api/auth';
	import { isApiError } from '$lib/api/errors';
	import { getOnboardingRoute, isOnboardingEditMode, resolveOnboardingGuard } from '$lib/auth/routing';
	import { createProfile, getProfile, updateProfile } from '$lib/api/profile';
	import { authUser, logout, updateUser } from '$lib/stores/auth';
	import type { ProfileCreateRequest, StudentProfile } from '$lib/types';

	let saving = $state(false);
	let errorMessage: string | null = $state(null);
	let loadingProfile = $state(false);
	let initialData: ProfileCreateRequest | null = $state(null);

	const user = fromStore(authUser);
	const editMode = $derived(isOnboardingEditMode(page.url));

	function toProfileFormData(profile: StudentProfile): ProfileCreateRequest {
		return {
			age: profile.age,
			education_level: profile.education_level,
			interests: profile.interests,
			learning_style: profile.learning_style,
			preferred_notation: profile.preferred_notation,
			prior_knowledge: profile.prior_knowledge,
			goals: profile.goals,
			preferred_depth: profile.preferred_depth,
			learner_description: profile.learner_description
		};
	}

	onMount(async () => {
		const redirectTo = resolveOnboardingGuard(user.current, editMode);
		if (redirectTo) {
			goto(redirectTo, { replaceState: true });
			return;
		}

		if (!editMode) {
			return;
		}

		loadingProfile = true;
		try {
			const profile = await getProfile();
			initialData = toProfileFormData(profile);
		} catch (err) {
			if (isApiError(err) && err.status === 401) {
				logout();
				goto('/login', { replaceState: true });
				return;
			}

			if (isApiError(err) && err.status === 404) {
				goto(getOnboardingRoute(), { replaceState: true });
				return;
			}

			errorMessage = err instanceof Error ? err.message : 'Failed to load your profile.';
		} finally {
			loadingProfile = false;
		}
	});

	async function handleSubmit(data: ProfileCreateRequest) {
		saving = true;
		errorMessage = null;

		try {
			if (editMode) {
				await updateProfile(data);
			} else {
				await createProfile(data);
			}

			try {
				const refreshedUser = await fetchCurrentUser();
				updateUser(refreshedUser);
			} catch {
				if (user.current) {
					updateUser({ ...user.current, has_profile: true });
				}
			}

			goto('/dashboard', { replaceState: true });
		} catch (err) {
			if (isApiError(err) && err.status === 401) {
				logout();
				goto('/login', { replaceState: true });
				return;
			}

			errorMessage = err instanceof Error ? err.message : 'Failed to save profile.';
		} finally {
			saving = false;
		}
	}
</script>

<div class="onboarding">
	<h1>{editMode ? 'Update your profile' : `Welcome${user.current?.name ? `, ${user.current.name}` : ''}!`}</h1>
	<p>
		{#if editMode}
			Refresh your learning profile to keep textbook generation aligned with your current goals.
		{:else}
			Let's set up your learning profile. This helps us generate textbooks that are personalized to your needs.
		{/if}
	</p>

	{#if loadingProfile}
		<p>Loading your profile...</p>
	{:else}
		<ProfileSetup
			onsubmit={handleSubmit}
			disabled={saving}
			initialData={initialData}
			submitLabel={editMode ? 'Save Profile' : 'Complete Setup'}
		/>
	{/if}

	{#if errorMessage}
		<p class="error">{errorMessage}</p>
	{/if}
</div>

<style>
	.onboarding {
		max-width: 650px;
	}

	h1 {
		margin-bottom: 0.25rem;
	}

	p {
		color: #aaa;
		margin-bottom: 1.5rem;
	}

	.error {
		color: #e57373;
		margin-top: 1rem;
	}
</style>

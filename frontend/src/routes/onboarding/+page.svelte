<script lang="ts">
	import { goto } from '$app/navigation';
	import { createProfile } from '$lib/api/profile';
	import ProfileSetup from '$lib/components/ProfileSetup.svelte';
	import { getUser, updateUser } from '$lib/stores/auth';
	import type { ProfileCreateRequest } from '$lib/types';

	let saving = $state(false);
	let errorMessage: string | null = $state(null);

	const user = $derived(getUser());

	async function handleSubmit(data: ProfileCreateRequest) {
		saving = true;
		errorMessage = null;
		try {
			await createProfile(data);
			if (user) {
				updateUser({ ...user, has_profile: true });
			}
			goto('/dashboard');
		} catch (err) {
			errorMessage = err instanceof Error ? err.message : 'Failed to save profile.';
		} finally {
			saving = false;
		}
	}
</script>

<div class="onboarding">
	<h1>Welcome{user?.name ? `, ${user.name}` : ''}!</h1>
	<p>Let's set up your learning profile. This helps us generate textbooks that are personalized to your needs.</p>

	<ProfileSetup onsubmit={handleSubmit} disabled={saving} />

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

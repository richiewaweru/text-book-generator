<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { getUser } from '$lib/stores/auth';
	import { getProfile } from '$lib/api/profile';
	import { startGeneration, pollUntilDone } from '$lib/api/client';
	import ProfileForm from '$lib/components/ProfileForm.svelte';
	import GenerationProgress from '$lib/components/GenerationProgress.svelte';
	import type { StudentProfile, GenerationRequest, GenerationStatus } from '$lib/types';

	const user = $derived(getUser());

	let profile: StudentProfile | null = $state(null);
	let loadingProfile = $state(true);
	let generationStatus: GenerationStatus | null = $state(null);
	let generating = $state(false);
	let errorMessage: string | null = $state(null);

	onMount(async () => {
		try {
			profile = await getProfile();
		} catch {
			goto('/onboarding');
		} finally {
			loadingProfile = false;
		}
	});

	async function handleGenerate(request: GenerationRequest) {
		generating = true;
		errorMessage = null;
		generationStatus = null;

		try {
			const { generation_id } = await startGeneration(request);

			const finalStatus = await pollUntilDone(generation_id, (s) => {
				generationStatus = s;
			});

			if (finalStatus.status === 'completed' && finalStatus.result) {
				goto(`/textbook/${finalStatus.result.textbook_id}`);
			} else if (finalStatus.status === 'failed') {
				errorMessage = finalStatus.error ?? 'Generation failed unexpectedly.';
			}
		} catch (err) {
			errorMessage = err instanceof Error ? err.message : 'An unknown error occurred.';
		} finally {
			generating = false;
		}
	}
</script>

<div class="dashboard">
	{#if loadingProfile}
		<p>Loading your profile...</p>
	{:else if profile}
		<div class="welcome-section">
			<h1>Welcome back{user?.name ? `, ${user.name}` : ''}</h1>
			<p class="subtitle">Your personalized textbook generator is ready.</p>
		</div>

		<div class="profile-summary">
			<h2>Your Profile</h2>
			<div class="profile-grid">
				<div class="profile-item">
					<span class="label">Education</span>
					<span class="value">{profile.education_level.replace('_', ' ')}</span>
				</div>
				<div class="profile-item">
					<span class="label">Age</span>
					<span class="value">{profile.age}</span>
				</div>
				<div class="profile-item">
					<span class="label">Learning Style</span>
					<span class="value">{profile.learning_style.replace('_', ' ')}</span>
				</div>
				<div class="profile-item">
					<span class="label">Notation</span>
					<span class="value">{profile.preferred_notation.replace('_', ' ')}</span>
				</div>
				{#if profile.interests.length > 0}
					<div class="profile-item wide">
						<span class="label">Interests</span>
						<span class="value">{profile.interests.join(', ')}</span>
					</div>
				{/if}
			</div>
			<button class="edit-profile-btn" onclick={() => goto('/onboarding')}>Edit Profile</button>
		</div>

		<div class="generate-section">
			<h2>Generate a Textbook</h2>
			<p>Tell us what you want to learn. We'll combine this with your profile to create a personalized textbook.</p>
			<ProfileForm onsubmit={handleGenerate} disabled={generating} />
		</div>

		{#if generationStatus}
			<GenerationProgress status={generationStatus} />
		{/if}

		{#if errorMessage}
			<div class="error">
				<p><strong>Error:</strong> {errorMessage}</p>
			</div>
		{/if}
	{/if}
</div>

<style>
	.dashboard {
		max-width: 800px;
	}

	.welcome-section {
		margin-bottom: 2rem;
	}

	.welcome-section h1 {
		margin-bottom: 0.25rem;
	}

	.subtitle {
		color: #888;
		font-size: 1.05rem;
	}

	.profile-summary {
		background: #1a1a1a;
		border: 1px solid #333;
		border-radius: 8px;
		padding: 1.5rem;
		margin-bottom: 2rem;
	}

	.profile-summary h2 {
		margin: 0 0 1rem 0;
		font-size: 1.15rem;
	}

	.profile-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
		gap: 0.75rem;
		margin-bottom: 1rem;
	}

	.profile-item {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
	}

	.profile-item.wide {
		grid-column: 1 / -1;
	}

	.label {
		font-size: 0.8rem;
		color: #888;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.value {
		font-size: 0.95rem;
		color: #ddd;
		text-transform: capitalize;
	}

	.edit-profile-btn {
		background: none;
		border: 1px solid #555;
		color: #aaa;
		padding: 0.3rem 0.8rem;
		border-radius: 4px;
		cursor: pointer;
		font-size: 0.85rem;
	}

	.edit-profile-btn:hover {
		border-color: #888;
		color: #ddd;
	}

	.generate-section {
		margin-bottom: 2rem;
	}

	.generate-section h2 {
		font-size: 1.15rem;
		margin-bottom: 0.25rem;
	}

	.generate-section p {
		color: #888;
		margin-bottom: 1rem;
	}

	.error {
		background: #2a1515;
		border: 1px solid #5a2020;
		border-radius: 6px;
		padding: 1rem;
		margin-top: 1rem;
	}

	.error p {
		margin: 0;
		color: #e57373;
	}
</style>

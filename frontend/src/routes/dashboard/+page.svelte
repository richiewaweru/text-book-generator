<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { fromStore } from 'svelte/store';
	import { basePresetMap, templateRegistryMap } from 'lectio';
	import { isApiError } from '$lib/api/errors';
	import { getOnboardingRoute, resolveDashboardProfileFailure } from '$lib/auth/routing';
	import { getGenerations } from '$lib/api/client';
	import { friendlyGenerationErrorMessage } from '$lib/generation/error-messages';
	import { getProfile } from '$lib/api/profile';
	import { authUser, logout } from '$lib/stores/auth';
	import { getTextbookRoute } from '$lib/navigation/textbook';
	import type { TeacherProfile, GenerationHistoryItem } from '$lib/types';

	const user = fromStore(authUser);

	let profile = $state<TeacherProfile | null>(null);
	let pastGenerations = $state<GenerationHistoryItem[]>([]);
	let loadingProfile = $state(true);
	let profileErrorMessage = $state<string | null>(null);
	const savedGenerations = $derived(
		pastGenerations.filter((generation) => generation.status === 'completed')
	);
	const activeGenerations = $derived(
		pastGenerations.filter((generation) => generation.status !== 'completed')
	);

	onMount(async () => {
		try {
			profile = await getProfile();
		} catch (err) {
			const resolution = resolveDashboardProfileFailure(err);
			if (resolution.redirectTo) {
				if (resolution.redirectTo === '/login') {
					logout();
				}
				goto(resolution.redirectTo, { replaceState: true });
				return;
			}
			profileErrorMessage = resolution.message ?? 'Failed to load your profile.';
			return;
		} finally {
			loadingProfile = false;
		}

		try {
			pastGenerations = await getGenerations();
		} catch (err) {
			if (isApiError(err) && err.status === 401) {
				logout();
				goto('/login', { replaceState: true });
			}
		}
	});

	function templateName(templateId: string | null): string {
		return (templateId && templateRegistryMap[templateId]?.contract.name) ?? templateId ?? 'Unknown template';
	}

	function presetName(presetId: string | null): string {
		return (presetId && basePresetMap[presetId]?.name) ?? presetId ?? 'Unknown preset';
	}
</script>

<div class="dashboard">
	{#if loadingProfile}
		<p>Loading your profile...</p>
	{:else if profileErrorMessage}
		<div class="error">
			<p><strong>Error:</strong> {profileErrorMessage}</p>
		</div>
	{:else if profile}
		<section class="welcome-section">
			<div>
				<p class="eyebrow">Shell + Pipeline</p>
				<h1>Welcome back{user.current?.name ? `, ${user.current.name}` : ''}</h1>
				<p class="subtitle">
					Your saved teacher profile powers workspace defaults, while Studio remains the place where each lesson gets planned and generated.
				</p>
			</div>
		</section>

		<section class="profile-summary">
			<h2>Teacher Setup</h2>
			<div class="profile-grid">
				<div class="profile-item">
					<span class="label">Teacher Role</span>
					<span class="value">{profile.teacher_role.replace('_', ' ')}</span>
				</div>
				<div class="profile-item">
					<span class="label">Default Grade Band</span>
					<span class="value">{profile.default_grade_band.replace('_', ' ')}</span>
				</div>
				<div class="profile-item">
					<span class="label">Tone</span>
					<span class="value">{profile.delivery_preferences.tone.replace('_', ' ')}</span>
				</div>
				<div class="profile-item">
					<span class="label">Brevity</span>
					<span class="value">{profile.delivery_preferences.brevity.replace('_', ' ')}</span>
				</div>
				{#if profile.subjects.length > 0}
					<div class="profile-item wide">
						<span class="label">Subjects</span>
						<span class="value">{profile.subjects.join(', ')}</span>
					</div>
				{/if}
				{#if profile.default_audience_description}
					<div class="profile-item wide">
						<span class="label">Default Audience</span>
						<span class="value">{profile.default_audience_description}</span>
					</div>
				{/if}
				{#if profile.curriculum_framework}
					<div class="profile-item wide">
						<span class="label">Curriculum</span>
						<span class="value">{profile.curriculum_framework}</span>
					</div>
				{/if}
				{#if profile.classroom_context}
					<div class="profile-item wide">
						<span class="label">Classroom Context</span>
						<span class="value">{profile.classroom_context}</span>
					</div>
				{/if}
				{#if profile.planning_goals}
					<div class="profile-item wide">
						<span class="label">Planning Goals</span>
						<span class="value">{profile.planning_goals}</span>
					</div>
				{/if}
			</div>
			<button class="edit-profile-btn" onclick={() => goto(getOnboardingRoute({ edit: true }))}>
				Edit Profile
			</button>
		</section>

		<section class="generate-section">
			<h2>Teacher Studio</h2>
			<p>
				The canonical lesson-creation flow now lives in the dedicated studio route. Open it to move
				through intent capture, streamed planning, review, and live generation in one workspace.
			</p>
			<div class="studio-entry studio-entry-prominent">
				<div class="studio-entry-copy">
					<p class="studio-kicker">Canonical flow</p>
					<h3>Create a lesson in Studio</h3>
					<p>
						Teachers now plan first, review explicitly, and watch sections generate live without
						leaving the workspace.
					</p>
					<div class="studio-features">
						<span>Intent capture</span>
						<span>Streamed planning</span>
						<span>Editable review</span>
						<span>Live generation</span>
					</div>
				</div>
				<div class="studio-entry-actions">
					<a href="/studio" class="studio-link">Open Studio</a>
					<button class="ghost-link" onclick={() => goto('/studio')}>Resume planning</button>
				</div>
			</div>
		</section>

		{#if savedGenerations.length > 0}
			<section class="history-section">
				<h2>Saved Books</h2>
				<ul class="history-list">
					{#each savedGenerations as gen}
						<li class="history-item">
							<div class="history-info">
								<p class="history-subject">{gen.subject}</p>
								<div class="history-meta">
									<span class="status status-{gen.status}">{gen.status}</span>
									<span>{templateName(gen.resolved_template_id ?? gen.requested_template_id)}</span>
									<span>{presetName(gen.resolved_preset_id ?? gen.requested_preset_id)}</span>
								</div>
								{#if gen.status === 'failed'}
									<p class="failure-copy">
										{friendlyGenerationErrorMessage(null, gen.error_type, gen.error_code)}
									</p>
								{/if}
							</div>
							<div class="history-actions">
								<a href={getTextbookRoute(gen.id)} class="view-link">Open</a>
							</div>
						</li>
					{/each}
				</ul>
			</section>
		{/if}

		{#if activeGenerations.length > 0}
			<section class="history-section">
				<h2>Generation Activity</h2>
				<ul class="history-list">
					{#each activeGenerations as gen}
						<li class="history-item">
							<div class="history-info">
								<p class="history-subject">{gen.subject}</p>
								<div class="history-meta">
									<span class="status status-{gen.status}">{gen.status}</span>
									<span>{templateName(gen.resolved_template_id ?? gen.requested_template_id)}</span>
									<span>{presetName(gen.resolved_preset_id ?? gen.requested_preset_id)}</span>
								</div>
								{#if gen.status === 'failed'}
									<p class="failure-copy">
										{friendlyGenerationErrorMessage(null, gen.error_type, gen.error_code)}
									</p>
								{/if}
							</div>
							<div class="history-actions">
								<a href={getTextbookRoute(gen.id)} class="view-link">Open</a>
							</div>
						</li>
					{/each}
				</ul>
			</section>
		{/if}
	{/if}
</div>

<style>
	.dashboard {
		display: grid;
		gap: 1.5rem;
	}

	.welcome-section,
	.profile-summary,
	.generate-section,
	.history-section {
		border: 1px solid rgba(36, 52, 63, 0.12);
		border-radius: 26px;
		background: rgba(255, 251, 244, 0.84);
		box-shadow: 0 18px 50px rgba(72, 52, 23, 0.08);
		padding: 1.35rem;
	}

	.eyebrow {
		margin: 0 0 0.3rem 0;
		font-size: 0.78rem;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: #6b7c88;
	}

	.welcome-section h1,
	.profile-summary h2,
	.generate-section h2,
	.history-section h2 {
		margin: 0;
	}

	.subtitle,
	.generate-section > p {
		color: #655c52;
		max-width: 60ch;
	}

	.profile-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
		gap: 0.8rem;
		margin: 1rem 0;
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
		font-size: 0.78rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: #6f6b63;
	}

	.value {
		color: #1f1c18;
		text-transform: capitalize;
	}

	.edit-profile-btn,
	.studio-link,
	.ghost-link {
		border-radius: 999px;
		border: 1px solid rgba(36, 52, 63, 0.18);
		background: rgba(36, 52, 63, 0.05);
		color: #24343f;
		padding: 0.45rem 0.85rem;
		cursor: pointer;
	}

	.studio-entry {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		padding: 0.9rem 1rem;
		border-radius: 18px;
		background: rgba(255, 255, 255, 0.58);
		border: 1px solid rgba(36, 52, 63, 0.08);
		margin: 1rem 0;
	}

	.studio-entry-prominent {
		align-items: stretch;
		padding: 1.1rem 1.15rem;
	}

	.studio-entry-copy {
		display: grid;
		gap: 0.45rem;
		color: #655c52;
	}

	.studio-entry-copy p,
	.studio-entry-copy h3 {
		margin: 0;
	}

	.studio-kicker {
		font-size: 0.76rem;
		font-weight: 700;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: #6b7c88;
	}

	.studio-features {
		display: flex;
		flex-wrap: wrap;
		gap: 0.45rem;
		margin-top: 0.2rem;
	}

	.studio-features span {
		border-radius: 999px;
		background: rgba(29, 158, 117, 0.1);
		padding: 0.22rem 0.65rem;
		font-size: 0.78rem;
		color: #0b6a52;
	}

	.studio-entry-actions {
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
		justify-content: center;
		min-width: 12rem;
	}

	.studio-link {
		text-decoration: none;
		white-space: nowrap;
		text-align: center;
	}

	.ghost-link {
		background: rgba(255, 255, 255, 0.7);
	}

	.history-list {
		list-style: none;
		padding: 0;
		margin: 1rem 0 0 0;
		display: grid;
		gap: 0.85rem;
	}

	.history-item {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
		padding: 1rem;
		border-radius: 18px;
		background: rgba(255, 255, 255, 0.72);
		border: 1px solid rgba(36, 52, 63, 0.1);
	}

	.history-subject {
		margin: 0;
		font-size: 1rem;
		font-weight: 700;
	}

	.history-meta {
		display: flex;
		flex-wrap: wrap;
		gap: 0.55rem;
		margin-top: 0.5rem;
		color: #5e554b;
		font-size: 0.9rem;
	}

	.status {
		padding: 0.2rem 0.55rem;
		border-radius: 999px;
		font-size: 0.76rem;
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}

	.status-pending,
	.status-running {
		background: rgba(54, 101, 130, 0.12);
		color: #28516b;
	}

	.status-completed {
		background: rgba(61, 120, 73, 0.13);
		color: #276135;
	}

	.status-failed {
		background: rgba(148, 66, 46, 0.12);
		color: #8d3a26;
	}

	.view-link {
		color: #24436a;
		font-weight: 600;
		text-decoration: none;
	}

	.history-actions {
		display: flex;
		gap: 0.6rem;
		align-items: center;
	}

	.failure-copy {
		margin: 0.5rem 0 0 0;
		color: #864635;
		font-size: 0.9rem;
	}

	@media (max-width: 720px) {
		.studio-entry,
		.history-item {
			display: grid;
		}

		.studio-entry-actions {
			min-width: auto;
		}
	}
</style>

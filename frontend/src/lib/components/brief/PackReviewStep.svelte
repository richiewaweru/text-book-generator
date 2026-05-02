<script lang="ts">
	import {
		depthOptions,
		gradeLevelLabel,
		outcomeOptions,
		resolvePreviewDepth,
		supportOptions
	} from '$lib/brief/config';
	import type { PackResourcePreview } from '$lib/brief/config';
	import type { TeacherBrief } from '$lib/types';

	let {
		brief,
		enabledResources,
		loading,
		error,
		onBack,
		onGenerate
	}: {
		brief: Partial<TeacherBrief>;
		enabledResources: PackResourcePreview[];
		loading: boolean;
		error: string | null;
		onBack: () => void;
		onGenerate: () => void;
	} = $props();

	const outcomeLabel = $derived(
		outcomeOptions.find((option) => option.value === brief.intended_outcome)?.label ?? 'Not set'
	);
	const depthLabel = $derived(
		depthOptions.find((option) => option.value === brief.depth)?.label ?? 'Standard'
	);
	const supportsText = $derived(
		brief.supports?.length
			? brief.supports
					.map((support) => supportOptions.find((option) => option.value === support)?.label ?? support)
					.join(', ')
			: 'None selected'
	);
</script>

<section class="pack-review">
	<header>
		<p class="eyebrow">Pack Review</p>
		<h2>{brief.topic ?? 'Learning Pack'}</h2>
		<p class="lede">
			Review the captured signals for this pack. Generation will use exactly this composition.
		</p>
	</header>

	<div class="signals-grid">
		<div class="signal-card">
			<span class="signal-label">Subject</span>
			<strong>{brief.subject ?? 'Not set'}</strong>
		</div>
		<div class="signal-card">
			<span class="signal-label">Topic</span>
			<strong>{brief.topic ?? 'Not set'}</strong>
		</div>
		<div class="signal-card">
			<span class="signal-label">Subtopics</span>
			<strong>{brief.subtopics?.join(', ') ?? 'Not set'}</strong>
		</div>
		<div class="signal-card">
			<span class="signal-label">Grade</span>
			<strong>{brief.grade_level ? gradeLevelLabel(brief.grade_level) : 'Not set'}</strong>
		</div>
		<div class="signal-card">
			<span class="signal-label">Outcome</span>
			<strong>{outcomeLabel}</strong>
		</div>
		<div class="signal-card">
			<span class="signal-label">Supports</span>
			<strong>{supportsText}</strong>
		</div>
		<div class="signal-card">
			<span class="signal-label">Depth</span>
			<strong>{depthLabel} (standard resources)</strong>
		</div>
	</div>

	<div class="resources-section">
		<p class="section-label">Resources in this pack</p>
		<ul class="resource-list">
			{#each enabledResources as resource}
				<li class="resource-item">
					<div class="resource-name-row">
						<strong>{resource.label}</strong>
						<span class="depth-badge">
							{resolvePreviewDepth(resource, brief.depth ?? 'standard')}
						</span>
					</div>
					<p class="resource-purpose">{resource.purpose}</p>
				</li>
			{/each}
		</ul>
	</div>

	{#if error}
		<p class="error-notice">{error}</p>
	{/if}

	<div class="actions">
		<button type="button" class="back-btn" onclick={onBack} disabled={loading}>Back</button>
		<button type="button" class="generate-btn" onclick={onGenerate} disabled={loading}>
			{loading
				? 'Planning pack...'
				: `Generate ${enabledResources.length} resource${enabledResources.length === 1 ? '' : 's'} ->`}
		</button>
	</div>
</section>

<style>
	.pack-review {
		display: grid;
		gap: 1.25rem;
	}

	.eyebrow {
		margin: 0 0 0.3rem;
		font-size: 0.72rem;
		font-weight: 700;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: #6b7c88;
	}

	h2 {
		margin: 0 0 0.35rem;
	}

	.lede {
		margin: 0;
		font-size: 0.88rem;
		color: #655c52;
		line-height: 1.55;
	}

	.signals-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 0.75rem;
	}

	.signal-card {
		border: 1px solid rgba(36, 52, 63, 0.1);
		border-radius: 14px;
		background: white;
		padding: 0.8rem 0.95rem;
	}

	.signal-label {
		display: block;
		font-size: 0.72rem;
		font-weight: 700;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: #6b7c88;
		margin-bottom: 0.3rem;
	}

	.section-label {
		margin: 0 0 0.6rem;
		font-size: 0.82rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: #6b7c88;
	}

	.resource-list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		gap: 0.5rem;
	}

	.resource-item {
		border: 1px solid rgba(36, 52, 63, 0.1);
		border-radius: 12px;
		background: white;
		padding: 0.75rem 1rem;
	}

	.resource-name-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.25rem;
	}

	.depth-badge {
		font-size: 0.7rem;
		font-weight: 600;
		padding: 0.15rem 0.5rem;
		border-radius: 999px;
		background: rgba(36, 52, 63, 0.07);
		color: #4f5c65;
	}

	.resource-purpose {
		margin: 0;
		font-size: 0.82rem;
		color: #807670;
		line-height: 1.4;
	}

	.error-notice {
		margin: 0;
		padding: 0.75rem 1rem;
		border-radius: 12px;
		background: #fff2ee;
		color: #7d3524;
		font-size: 0.88rem;
	}

	.actions {
		display: flex;
		justify-content: space-between;
		gap: 0.75rem;
	}

	.back-btn {
		border: 1px solid rgba(36, 52, 63, 0.15);
		border-radius: 999px;
		background: transparent;
		color: #4f5c65;
		padding: 0.75rem 1rem;
		font-weight: 600;
		cursor: pointer;
	}

	.generate-btn {
		border: 0;
		border-radius: 999px;
		background: #0b6a52;
		color: white;
		padding: 0.8rem 1.25rem;
		font-weight: 700;
		font-size: 0.95rem;
		cursor: pointer;
	}

	.generate-btn:disabled,
	.back-btn:disabled {
		opacity: 0.45;
		cursor: not-allowed;
	}
</style>

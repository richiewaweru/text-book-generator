<script lang="ts">
	import {
		outcomeOptions,
		packPreviewByOutcome,
		resolvePreviewDepth,
		type PackResourcePreview
	} from '$lib/brief/config';
	import type { TeacherBrief, TeacherBriefOutcome } from '$lib/types';

	let {
		brief,
		loading,
		onGenerate
	}: {
		brief: Partial<TeacherBrief>;
		loading: boolean;
		onGenerate: (enabledResources: PackResourcePreview[]) => void;
	} = $props();

	const outcome = $derived(brief.intended_outcome as TeacherBriefOutcome | undefined);
	const depth = $derived(brief.depth ?? 'standard');
	const resources = $derived((outcome ? packPreviewByOutcome[outcome] : []) ?? []);
	const outcomeLabel = $derived(
		outcomeOptions.find((option) => option.value === outcome)?.label ?? 'this lesson'
	);

	let enabled = $state<Record<string, boolean>>({});

	$effect(() => {
		const next: Record<string, boolean> = {};
		for (const resource of resources) {
			next[resource.resourceType] = enabled[resource.resourceType] ?? true;
		}
		const keys = Object.keys(next);
		const sameSize = keys.length === Object.keys(enabled).length;
		const unchanged = sameSize && keys.every((key) => enabled[key] === next[key]);
		if (!unchanged) {
			enabled = next;
		}
	});

	const enabledResources = $derived(resources.filter((resource) => enabled[resource.resourceType]));
	const enabledCount = $derived(enabledResources.length);

	function toggle(resourceType: string, required: boolean) {
		if (required) return;
		enabled = { ...enabled, [resourceType]: !enabled[resourceType] };
	}
</script>

<div class="pack-card">
	<div class="pack-header">
		<div>
			<p class="eyebrow">Learning Pack</p>
			<h3>Build a coordinated set</h3>
			<p class="pack-desc">
				Based on <strong>{outcomeLabel}</strong>. {resources.length} resources share one
				objective, vocabulary, and anchor examples.
			</p>
		</div>
	</div>

	{#if resources.length === 0}
		<p class="empty">Select an outcome to preview the learning pack.</p>
	{:else}
		<ul class="resource-list">
			{#each resources as resource}
				{@const isEnabled = enabled[resource.resourceType] ?? true}
				{@const isRequired = !resource.optional}
				<li class="resource-item" class:disabled={!isEnabled} class:required={isRequired}>
					<label class="resource-label">
						<input
							type="checkbox"
							checked={isEnabled}
							disabled={isRequired}
							onchange={() => toggle(resource.resourceType, isRequired)}
						/>
						<div class="resource-info">
							<div class="resource-name-row">
								<strong>{resource.label}</strong>
								<span class="depth-badge">{resolvePreviewDepth(resource, depth)}</span>
								{#if resource.optional}
									<span class="optional-badge">optional</span>
								{/if}
							</div>
							<p class="resource-purpose">{resource.purpose}</p>
						</div>
					</label>
				</li>
			{/each}
		</ul>

		{#if brief.supports?.length}
			<p class="supports-note">
				Supports applied to all resources:
				<strong>{brief.supports.join(', ').replaceAll('_', ' ')}</strong>
			</p>
		{/if}

		<button
			type="button"
			class="generate-btn"
			disabled={enabledCount === 0 || loading}
			onclick={() => onGenerate(enabledResources)}
		>
			{loading
				? 'Planning pack...'
				: `Generate ${enabledCount} resource${enabledCount === 1 ? '' : 's'} ->`}
		</button>
	{/if}
</div>

<style>
	.pack-card {
		display: grid;
		gap: 1rem;
		border: 1px solid rgba(29, 158, 117, 0.22);
		border-radius: 20px;
		background: linear-gradient(
			135deg,
			rgba(29, 158, 117, 0.04) 0%,
			rgba(255, 255, 255, 0.9) 100%
		);
		padding: 1.25rem;
	}

	.pack-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 1rem;
	}

	.eyebrow {
		margin: 0 0 0.3rem;
		font-size: 0.72rem;
		font-weight: 700;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: #0b6a52;
	}

	h3 {
		margin: 0 0 0.3rem;
		font-size: 1.05rem;
	}

	.pack-desc {
		margin: 0;
		font-size: 0.88rem;
		color: #655c52;
		line-height: 1.5;
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
		border-radius: 14px;
		background: white;
		padding: 0.8rem 1rem;
		transition: opacity 0.15s;
	}

	.resource-item.disabled {
		opacity: 0.45;
	}

	.resource-item.required {
		border-color: rgba(29, 158, 117, 0.18);
	}

	.resource-label {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0.75rem;
		align-items: start;
		cursor: pointer;
	}

	.resource-label input[type='checkbox']:disabled {
		cursor: default;
		opacity: 0.4;
	}

	.resource-info {
		display: grid;
		gap: 0.3rem;
	}

	.resource-name-row {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.resource-name-row strong {
		font-size: 0.9rem;
	}

	.depth-badge {
		font-size: 0.72rem;
		font-weight: 600;
		padding: 0.15rem 0.5rem;
		border-radius: 999px;
		background: rgba(36, 52, 63, 0.07);
		color: #4f5c65;
	}

	.optional-badge {
		font-size: 0.72rem;
		font-weight: 500;
		padding: 0.15rem 0.5rem;
		border-radius: 999px;
		background: rgba(180, 160, 100, 0.1);
		color: #7a6b3a;
	}

	.resource-purpose {
		margin: 0;
		font-size: 0.82rem;
		color: #807670;
		line-height: 1.45;
	}

	.supports-note {
		margin: 0;
		font-size: 0.82rem;
		color: #655c52;
		padding: 0.6rem 0.8rem;
		background: rgba(29, 158, 117, 0.05);
		border-radius: 10px;
	}

	.generate-btn {
		justify-self: stretch;
		border: 0;
		border-radius: 999px;
		background: #0b6a52;
		color: white;
		padding: 0.85rem 1.2rem;
		font-weight: 700;
		font-size: 0.95rem;
		cursor: pointer;
		transition: opacity 0.15s;
	}

	.generate-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.generate-btn:hover:not(:disabled) {
		opacity: 0.88;
	}

	.empty {
		margin: 0;
		font-size: 0.88rem;
		color: #9a9086;
	}
</style>

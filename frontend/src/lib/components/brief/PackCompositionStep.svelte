<script lang="ts">
	import { packPreviewByOutcome, resolvePreviewDepth } from '$lib/brief/config';
	import type { PackResourcePreview } from '$lib/brief/config';
	import type { TeacherBriefDepth, TeacherBriefOutcome } from '$lib/types';

	let {
		outcome,
		depth = 'standard',
		enabledResourceTypes,
		onToggle,
		onContinue
	}: {
		outcome?: TeacherBriefOutcome;
		depth?: TeacherBriefDepth;
		enabledResourceTypes: string[];
		onToggle: (resourceType: string, enabled: boolean) => void;
		onContinue: (enabledResources: PackResourcePreview[]) => void;
	} = $props();

	const resources = $derived((outcome ? packPreviewByOutcome[outcome] : []) ?? []);
	const enabledResources = $derived(
		resources.filter((resource) => enabledResourceTypes.includes(resource.resourceType))
	);
	const enabledCount = $derived(enabledResources.length);

	function isRequired(resource: PackResourcePreview): boolean {
		return resource.required || resource.optional === false;
	}

	function handleToggle(resource: PackResourcePreview) {
		if (isRequired(resource)) return;
		const nextEnabled = !enabledResourceTypes.includes(resource.resourceType);
		onToggle(resource.resourceType, nextEnabled);
	}
</script>

<div class="composition-step">
	<p class="helper">
		Choose what your pack contains. Required resources are always included; optional resources can be toggled.
	</p>

	{#if resources.length === 0}
		<p class="empty">Select an intended outcome first.</p>
	{:else}
		<ul class="resource-list">
			{#each resources as resource}
				{@const enabled = enabledResourceTypes.includes(resource.resourceType)}
				{@const required = isRequired(resource)}
				<li class="resource-item" class:dimmed={!enabled}>
					<label class="resource-label">
						<input
							type="checkbox"
							checked={enabled}
							disabled={required}
							onchange={() => handleToggle(resource)}
						/>
						<div class="resource-body">
							<div class="resource-name-row">
								<strong>{resource.label}</strong>
								<span class="depth-badge">{resolvePreviewDepth(resource, depth)}</span>
								{#if !required}
									<span class="optional-tag">optional</span>
								{/if}
							</div>
							<p class="resource-purpose">{resource.purpose}</p>
						</div>
					</label>
				</li>
			{/each}
		</ul>

		<p class="count-note">{enabledCount} resources enabled</p>

		<button
			type="button"
			class="continue-btn"
			disabled={enabledCount === 0}
			onclick={() => onContinue(enabledResources)}
		>
			Continue with {enabledCount} resource{enabledCount === 1 ? '' : 's'} ->
		</button>
	{/if}
</div>

<style>
	.composition-step {
		display: grid;
		gap: 0.9rem;
	}

	.helper {
		margin: 0;
		color: #655c52;
		line-height: 1.5;
	}

	.resource-list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		gap: 0.6rem;
	}

	.resource-item {
		border: 1px solid rgba(36, 52, 63, 0.1);
		border-radius: 14px;
		background: white;
		padding: 0.85rem 1rem;
		transition: opacity 0.15s;
	}

	.resource-item.dimmed {
		opacity: 0.4;
	}

	.resource-label {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0.75rem;
		cursor: pointer;
		align-items: start;
	}

	.resource-label input[type='checkbox']:disabled {
		cursor: default;
	}

	.resource-body {
		display: grid;
		gap: 0.3rem;
	}

	.resource-name-row {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 0.45rem;
	}

	.resource-name-row strong {
		font-size: 0.9rem;
	}

	.depth-badge {
		font-size: 0.7rem;
		font-weight: 600;
		padding: 0.15rem 0.5rem;
		border-radius: 999px;
		background: rgba(36, 52, 63, 0.07);
		color: #4f5c65;
	}

	.optional-tag {
		font-size: 0.7rem;
		font-weight: 500;
		padding: 0.15rem 0.5rem;
		border-radius: 999px;
		background: rgba(180, 160, 100, 0.12);
		color: #7a6b3a;
	}

	.resource-purpose {
		margin: 0;
		font-size: 0.82rem;
		color: #807670;
		line-height: 1.45;
	}

	.count-note {
		margin: 0;
		font-size: 0.82rem;
		color: #9a9086;
	}

	.continue-btn {
		border: 0;
		border-radius: 999px;
		background: #1d9e75;
		color: white;
		padding: 0.8rem 1.1rem;
		font-weight: 700;
		cursor: pointer;
		justify-self: start;
	}

	.continue-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.empty {
		margin: 0;
		color: #807670;
	}
</style>

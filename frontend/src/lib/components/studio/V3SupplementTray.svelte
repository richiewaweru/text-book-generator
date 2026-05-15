<script lang="ts">
	import type { V3SupplementOption, V3SupplementResourceType } from '$lib/types/v3';

	interface Props {
		parentGenerationId: string;
		options: V3SupplementOption[];
		loading?: boolean;
		error?: string | null;
		unavailableReason?: string | null;
		onCreatePlan: (resourceType: V3SupplementResourceType) => void;
	}

	let {
		parentGenerationId: _parentGenerationId,
		options,
		loading = false,
		error = null,
		unavailableReason = null,
		onCreatePlan
	}: Props = $props();
</script>

{#if loading}
	<div class="mx-auto max-w-4xl px-4 pt-6">
		<p class="text-sm text-muted-foreground">Loading companion resources…</p>
	</div>
{:else if error}
	<div class="mx-auto max-w-4xl px-4 pt-6">
		<p class="text-sm text-destructive" role="alert">{error}</p>
	</div>
{:else if unavailableReason}
	<div class="mx-auto max-w-4xl px-4 pt-6">
		<p class="text-sm text-muted-foreground">{unavailableReason}</p>
	</div>
{:else if options.length > 0}
	<section class="mx-auto max-w-4xl px-4 pt-6" aria-labelledby="supplement-tray-heading">
		<h2 id="supplement-tray-heading" class="text-lg font-semibold">Companion resources</h2>
		<p class="mt-1 text-sm text-muted-foreground">
			Build follow-up materials from the same teaching plan.
		</p>
		<ul class="mt-4 grid gap-4 sm:grid-cols-3">
			{#each options as option (option.resource_type)}
				<li class="flex flex-col rounded-xl border border-border/60 bg-card p-4 shadow-sm">
					<h3 class="font-semibold">{option.label}</h3>
					<p class="mt-2 flex-1 text-sm text-muted-foreground">{option.description}</p>
					{#if option.best_for}
						<p class="mt-2 text-xs text-muted-foreground">Best for: {option.best_for}</p>
					{/if}
					{#if option.estimated_length}
						<p class="text-xs text-muted-foreground">{option.estimated_length}</p>
					{/if}
					<button
						type="button"
						class="mt-4 rounded-md border border-input px-3 py-2 text-sm font-semibold hover:bg-muted/50"
						onclick={() => onCreatePlan(option.resource_type)}
					>
						{option.cta}
					</button>
				</li>
			{/each}
		</ul>
	</section>
{/if}

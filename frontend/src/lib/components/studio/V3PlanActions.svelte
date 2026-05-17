<script lang="ts">
	interface Props {
		failedSections?: string[];
		isRunning?: boolean;
		onApprove: () => void;
		onRegenerate: (note: string) => void;
		onRetrySection: (sectionId: string) => void;
	}

	let {
		failedSections = [],
		isRunning = false,
		onApprove,
		onRegenerate,
		onRetrySection
	}: Props = $props();

	let note = $state('');
	let showAdjust = $state(false);
	let showRegenerate = $state(false);

	function submitAdjust() {
		onRegenerate(note.trim());
		note = '';
		showAdjust = false;
	}

	function submitRegenerate() {
		onRegenerate(note.trim());
		note = '';
		showRegenerate = false;
	}
</script>

<div class="mx-auto max-w-3xl space-y-4 px-4 pb-10">
	<div class="flex flex-wrap gap-3">
		<button
			type="button"
			class="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-50"
			disabled={isRunning}
			onclick={onApprove}
		>
			Approve
		</button>
		<button
			type="button"
			class="rounded-md border border-input px-4 py-2 text-sm font-semibold"
			onclick={() => {
				showAdjust = !showAdjust;
				showRegenerate = false;
			}}
		>
			Adjust (regenerate with note)
		</button>
		<button
			type="button"
			class="rounded-md border border-input px-4 py-2 text-sm font-semibold"
			onclick={() => {
				showRegenerate = !showRegenerate;
				showAdjust = false;
			}}
		>
			Regenerate
		</button>
	</div>

	{#if showAdjust || showRegenerate}
		<div class="space-y-3 rounded-xl border border-border/60 bg-card p-4">
			<p class="text-sm text-muted-foreground">
				{showAdjust
					? 'Describe what to adjust; this will regenerate the structural plan with your note.'
					: 'Optional note for regeneration.'}
			</p>
			<textarea
				class="min-h-[90px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
				bind:value={note}
				placeholder="e.g. Keep section 2 shorter and add more warm practice."
			></textarea>
			<button
				type="button"
				class="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
				onclick={showAdjust ? submitAdjust : submitRegenerate}
			>
				Submit
			</button>
		</div>
	{/if}

	{#if failedSections.length}
		<div class="rounded-xl border border-destructive/30 bg-destructive/5 p-4">
			<p class="text-sm font-semibold text-destructive">Failed sections</p>
			<p class="mt-1 text-xs text-muted-foreground">
				Retry only the failed sections below, then assembly will run again automatically.
			</p>
			<div class="mt-3 flex flex-wrap gap-2">
				{#each failedSections as sectionId}
					<button
						type="button"
						class="rounded-md border border-input px-3 py-1.5 text-xs font-semibold"
						onclick={() => onRetrySection(sectionId)}
					>
						Retry {sectionId}
					</button>
				{/each}
			</div>
		</div>
	{/if}
</div>

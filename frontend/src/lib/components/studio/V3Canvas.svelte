<script lang="ts">
	import type { CanvasSection } from '$lib/types/v3';
	import type { V3Stage } from '$lib/types/v3';
	import V3CanvasSection from '$lib/components/studio/V3CanvasSection.svelte';

	interface Props {
		sections: CanvasSection[];
		stage: V3Stage | 'complete';
		templateId: string;
	}

	let { sections, stage, templateId }: Props = $props();

	const progressLabel: Record<string, string> = {
		generating: 'Writing your lesson…',
		finalising: 'Checking consistency…',
		complete: 'Resource ready'
	};
</script>

<div class="v3-canvas mx-auto max-w-3xl space-y-6 px-4 py-6">
	<div class="text-center text-sm text-muted-foreground" role="status" aria-live="polite">
		{progressLabel[stage] ?? ''}
	</div>

	<div class="space-y-8">
		{#each sections as section (section.id)}
			<V3CanvasSection {section} {templateId} />
		{/each}
	</div>
</div>

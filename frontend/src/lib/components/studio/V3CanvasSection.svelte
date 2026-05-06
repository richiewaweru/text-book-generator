<script lang="ts">
	import type { CanvasSection } from '$lib/types/v3';
	import V3CanvasComponent from '$lib/components/studio/V3CanvasComponent.svelte';
	import V3CanvasVisual from '$lib/components/studio/V3CanvasVisual.svelte';
	import V3LectioSectionEmbed from '$lib/components/studio/V3LectioSectionEmbed.svelte';

	interface Props {
		section: CanvasSection;
		templateId: string;
	}

	let { section, templateId }: Props = $props();
</script>

<div class="v3-canvas-section space-y-4 rounded-xl border border-border/60 bg-muted/20 p-4" id="section-{section.id}">
	<div class="flex flex-col gap-1 border-b border-border/40 pb-3">
		<h3 class="text-lg font-semibold tracking-tight">{section.title}</h3>
		<p class="text-xs text-muted-foreground">{section.teacher_labels}</p>
	</div>

	{#if section.visual}
		<V3CanvasVisual visual={section.visual} />
	{/if}

	<div class="space-y-2">
		{#each section.components as component (component.id)}
			<V3CanvasComponent {component} />
		{/each}
	</div>

	{#if section.questions.length}
		<div class="space-y-2">
			<h4 class="text-sm font-semibold">Practice</h4>
			{#each section.questions as q (q.id)}
				<div class="rounded-md border border-border/40 p-2 text-sm">
					<span class="mr-2 rounded bg-muted px-2 py-0.5 text-xs uppercase">{q.difficulty}</span>
					{#if q.status === 'pending'}
						<span class="text-muted-foreground">Waiting…</span>
					{:else}
						<span class="text-muted-foreground">Ready</span>
					{/if}
				</div>
			{/each}
		</div>
	{/if}

	<V3LectioSectionEmbed {templateId} sectionId={section.id} title={section.title} mergedFields={section.mergedFields} />

	<details class="rounded border border-border/40 bg-background/60 p-2">
		<summary class="cursor-pointer text-xs font-medium text-muted-foreground">Inspect section</summary>
		<pre class="mt-2 overflow-auto whitespace-pre-wrap text-[11px]">{JSON.stringify(section.mergedFields, null, 2)}</pre>
	</details>
</div>

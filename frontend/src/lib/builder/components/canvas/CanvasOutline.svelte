<script lang="ts">
	import { dragHandle, dragHandleZone, type DndEvent } from 'svelte-dnd-action';
	import { GripVertical } from 'lucide-svelte';
	import type { DocumentSection } from 'lectio';
	import type { DocumentStore } from '$lib/builder/stores/document.svelte';

	let { store }: { store: DocumentStore } = $props();

	let outlineItems = $state<DocumentSection[]>([]);

	$effect(() => {
		outlineItems = store.orderedSections.map((s) => ({ ...s }));
	});

	function handleConsider(e: CustomEvent<DndEvent<DocumentSection>>): void {
		outlineItems = e.detail.items as DocumentSection[];
	}

	function handleFinalize(e: CustomEvent<DndEvent<DocumentSection>>): void {
		outlineItems = e.detail.items as DocumentSection[];
		const ids = outlineItems.map((i) => i.id);
		store.reorderSections(ids);
	}
</script>

<nav
	class="canvas-outline w-52 shrink-0 border-l border-slate-200 bg-slate-50 p-4 text-sm"
	aria-label="Section outline"
>
	<p class="mb-3 font-semibold text-slate-700">Outline</p>
	<div
		use:dragHandleZone={{
			items: outlineItems,
			type: 'outline-section',
			flipDurationMs: 200,
			dropTargetStyle: { outline: '2px dashed #64748b' },
			dropFromOthersDisabled: true
		}}
		onconsider={handleConsider}
		onfinalize={handleFinalize}
	>
		{#each outlineItems as section (section.id)}
			<div class="mb-1 flex items-center gap-1">
				<span
					class="drag-handle inline-flex shrink-0 cursor-grab touch-none rounded p-0.5 text-slate-400 hover:bg-slate-200"
					aria-label="Drag to reorder sections"
					data-testid="outline-drag-handle"
					use:dragHandle
				>
					<GripVertical size={14} aria-hidden="true" />
				</span>
				<a
					href="#section-{section.id}"
					data-testid="outline-section-link"
					class="block min-w-0 flex-1 truncate rounded px-2 py-1 text-slate-600 hover:bg-slate-200 hover:text-slate-900"
					onclick={() => store.selectSection(section.id)}
				>
					{section.title}
				</a>
			</div>
		{/each}
	</div>
</nav>

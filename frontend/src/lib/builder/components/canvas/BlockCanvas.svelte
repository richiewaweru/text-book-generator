<script lang="ts">
	import { browser } from '$app/environment';
	import { dragHandleZone, type DndEvent } from 'svelte-dnd-action';
	import type { BlockInstance } from 'lectio';
	import type { DocumentStore } from '$lib/builder/stores/document.svelte';
	import AddSectionControl from './AddSectionControl.svelte';
	import BlockCard from './BlockCard.svelte';
	import SectionDivider from './SectionDivider.svelte';

	let { store }: { store: DocumentStore } = $props();

	let itemsBySection = $state<Record<string, BlockInstance[]>>({});
	let pendingDndMerge: Record<string, BlockInstance[]> = {};
	let rafFlush = 0;

	$effect(() => {
		const doc = store.document;
		if (!doc) {
			itemsBySection = {};
			return;
		}
		const next: Record<string, BlockInstance[]> = {};
		for (const s of store.orderedSections) {
			next[s.id] = store.blocksForSection(s).map((b) => ({ ...b })) as BlockInstance[];
		}
		itemsBySection = next;
	});

	function scheduleSyncFromDnd(): void {
		if (!browser) return;
		if (rafFlush) cancelAnimationFrame(rafFlush);
		rafFlush = requestAnimationFrame(() => {
			rafFlush = 0;
			const full: Record<string, BlockInstance[]> = {};
			for (const s of store.orderedSections) {
				full[s.id] = pendingDndMerge[s.id] ?? (store.blocksForSection(s) as BlockInstance[]);
			}
			pendingDndMerge = {};
			store.syncSectionsFromDnd(full);
		});
	}

	function handleConsider(sectionId: string, e: CustomEvent<DndEvent<BlockInstance>>): void {
		itemsBySection = { ...itemsBySection, [sectionId]: e.detail.items as BlockInstance[] };
	}

	function handleFinalize(sectionId: string, e: CustomEvent<DndEvent<BlockInstance>>): void {
		const items = e.detail.items as BlockInstance[];
		itemsBySection = { ...itemsBySection, [sectionId]: items };
		pendingDndMerge = { ...pendingDndMerge, [sectionId]: items };
		scheduleSyncFromDnd();
	}

	$effect(() => {
		if (!browser) return;
		const editingId = store.editingBlockId;
		if (!editingId) return;

		function onKey(e: KeyboardEvent): void {
			if (e.key === 'Escape') {
				store.stopEditing();
			}
		}

		function onPointerDown(e: PointerEvent): void {
			const target = e.target;
			if (!(target instanceof Node)) return;
			const inCard = (target as HTMLElement).closest?.(`[data-editing-card="${editingId}"]`);
			if (inCard) return;
			store.stopEditing();
		}

		window.addEventListener('keydown', onKey);
		document.addEventListener('pointerdown', onPointerDown, true);
		return () => {
			window.removeEventListener('keydown', onKey);
			document.removeEventListener('pointerdown', onPointerDown, true);
		};
	});
</script>

<div class="canvas mx-auto w-full max-w-4xl pb-16">
	<div class="rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-lg shadow-slate-300/25 sm:px-6 sm:py-6">
		{#each store.orderedSections as section, i (section.id)}
			<AddSectionControl {store} insertIndex={i} />
			<SectionDivider {section} {store} isFirstSection={i === 0} />

			<div
				class="min-h-[2rem]"
				use:dragHandleZone={{
					items: itemsBySection[section.id] ?? [],
					type: 'canvas-block',
					flipDurationMs: 200,
					dropTargetStyle: { outline: '2px dashed #3b82f6' },
					dragDisabled: !!store.editingBlockId
				}}
				onconsider={(e) => handleConsider(section.id, e)}
				onfinalize={(e) => handleFinalize(section.id, e)}
			>
				{#each itemsBySection[section.id] ?? [] as item (item.id)}
					<BlockCard
						block={item}
						document={store.document}
						{store}
						selected={store.selectedBlockId === item.id}
						editing={store.editingBlockId === item.id}
						onselect={() => store.selectBlock(item.id)}
						onstartedit={() => store.startEditing(item.id)}
						onstopedit={() => store.stopEditing()}
						onupdatefield={(field, value) => store.updateBlockField(item.id, field, value)}
						onfieldblur={() => store.notifyFieldBlur()}
						contextBlocksForAi={store.getContextBlocksForAi(item.id)}
						onapplyaicontent={(content) => {
							store.updateBlockContent(item.id, content);
							store.startEditing(item.id);
						}}
						onduplicate={() => {
							const nid = store.duplicateBlock(section.id, item.id);
							store.selectBlock(nid);
						}}
						ondelete={() => {
							if (confirm('Remove this block? You can undo.')) {
								store.removeBlock(section.id, item.id);
								const sec = store.document?.sections.find((s) => s.id === section.id);
								if (sec && sec.block_ids.length === 0) {
									if (
										confirm(
											'This section is now empty. Remove the section as well? You can undo.'
										)
									) {
										store.removeSection(section.id);
									}
								}
							}
						}}
					/>
				{/each}
			</div>
		{/each}
	</div>
	<div class="mx-auto mt-4 max-w-3xl rounded-xl border border-slate-200 bg-white/80 px-4 py-2 text-xs text-slate-600">
		Shortcuts: <span class="font-medium">Cmd/Ctrl+Z</span> undo, <span class="font-medium">Cmd/Ctrl+Shift+Z</span> redo, <span class="font-medium">Enter</span> edit block, <span class="font-medium">Esc</span> close edit.
	</div>
</div>

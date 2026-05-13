<script lang="ts">
	import { browser } from '$app/environment';
	import { dragHandle, dragHandleZone, type DndEvent } from 'svelte-dnd-action';
	import { getComponentById } from 'lectio';
	import type { DocumentStore } from '$lib/builder/stores/document.svelte';
	import { isPaletteDndItem, type DndRowItem } from '$lib/builder/stores/document.svelte';
	import AddSectionControl from './AddSectionControl.svelte';
	import BlockCard from './BlockCard.svelte';
	import SectionDivider from './SectionDivider.svelte';

	let { store }: { store: DocumentStore } = $props();

	let itemsBySection = $state<Record<string, DndRowItem[]>>({});
	let pendingDndMerge: Record<string, DndRowItem[]> = {};
	let rafFlush = 0;

	$effect(() => {
		const doc = store.document;
		if (!doc) {
			itemsBySection = {};
			return;
		}
		const next: Record<string, DndRowItem[]> = {};
		for (const s of store.orderedSections) {
			next[s.id] = store.blocksForSection(s).map((b) => ({ ...b })) as DndRowItem[];
		}
		itemsBySection = next;
	});

	function scheduleSyncFromDnd(): void {
		if (!browser) return;
		if (rafFlush) cancelAnimationFrame(rafFlush);
		rafFlush = requestAnimationFrame(() => {
			rafFlush = 0;
			const full: Record<string, DndRowItem[]> = {};
			for (const s of store.orderedSections) {
				full[s.id] = pendingDndMerge[s.id] ?? (store.blocksForSection(s) as DndRowItem[]);
			}
			pendingDndMerge = {};
			store.syncSectionsFromDnd(full);
		});
	}

	function handleConsider(sectionId: string, e: CustomEvent<DndEvent<DndRowItem>>): void {
		itemsBySection = { ...itemsBySection, [sectionId]: e.detail.items as DndRowItem[] };
	}

	function handleFinalize(sectionId: string, e: CustomEvent<DndEvent<DndRowItem>>): void {
		const items = e.detail.items as DndRowItem[];
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

<div class="canvas max-w-3xl flex-1 space-y-0 pb-16">
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
				{#if isPaletteDndItem(item)}
					<div
						class="mb-6 rounded-xl border-2 border-dashed border-blue-300 bg-blue-50/40 px-4 py-6 text-sm text-slate-700"
						data-testid="palette-drop-stub"
					>
						<div class="flex items-center gap-2">
							<span
								class="drag-handle inline-flex cursor-grab touch-none rounded p-1 text-slate-500 hover:bg-white/80 active:cursor-grabbing"
								aria-label="Drag to reorder"
								use:dragHandle
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									width="16"
									height="16"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									aria-hidden="true"
								>
									<circle cx="9" cy="5" r="1" fill="currentColor" stroke="none" />
									<circle cx="15" cy="5" r="1" fill="currentColor" stroke="none" />
									<circle cx="9" cy="12" r="1" fill="currentColor" stroke="none" />
									<circle cx="15" cy="12" r="1" fill="currentColor" stroke="none" />
									<circle cx="9" cy="19" r="1" fill="currentColor" stroke="none" />
									<circle cx="15" cy="19" r="1" fill="currentColor" stroke="none" />
								</svg>
							</span>
							<span class="font-medium"
								>{getComponentById(item.component_id)?.teacherLabel ?? item.component_id}</span
							>
							<span class="text-xs text-slate-500">(new block)</span>
						</div>
					</div>
				{:else}
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
				{/if}
			{/each}
		</div>
	{/each}
</div>

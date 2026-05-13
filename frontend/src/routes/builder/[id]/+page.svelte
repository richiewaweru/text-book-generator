<script lang="ts">
	import { browser } from '$app/environment';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import AppShell from '$lib/builder/components/shell/AppShell.svelte';
	import { createDocumentStore } from '$lib/builder/stores/document.svelte';
	import { getDocument } from '$lib/builder/persistence/idb-store';
	import {
		isDeleteOrBackspace,
		isModifierD,
		isModifierS,
		isModifierShiftZ,
		isModifierZ,
		isTextEditingTarget
	} from '$lib/builder/utils/shortcuts';

	const store = createDocumentStore();
	let ready = $state(false);

	const id = $derived(page.params.id);

	onMount(() => {
		if (!id) {
			void goto('/');
			return;
		}
		void getDocument(id).then(async (doc) => {
			if (!doc) {
				await goto('/');
				return;
			}
			store.loadDocument(doc);
			ready = true;
		});
	});

	$effect(() => {
		if (!browser || !ready || !store.document) return;

		function onKey(e: KeyboardEvent): void {
			if (isTextEditingTarget(e.target)) return;

			if (isModifierZ(e)) {
				e.preventDefault();
				store.undo();
				return;
			}
			if (isModifierShiftZ(e)) {
				e.preventDefault();
				store.redo();
				return;
			}
			if (isModifierS(e)) {
				e.preventDefault();
				void store.flushSave();
				return;
			}
			if (e.key === 'Escape') {
				if (store.editingBlockId) {
					store.stopEditing();
				} else {
					store.deselectBlock();
				}
				return;
			}
			if (e.key === 'Enter' && store.selectedBlockId && !store.editingBlockId) {
				e.preventDefault();
				store.startEditing(store.selectedBlockId);
				return;
			}
			if (isModifierD(e) && store.selectedBlockId) {
				e.preventDefault();
				const sid = store.getSectionIdForBlock(store.selectedBlockId);
				if (sid) {
					const nid = store.duplicateBlock(sid, store.selectedBlockId);
					store.selectBlock(nid);
				}
				return;
			}
			if (isDeleteOrBackspace(e) && store.selectedBlockId && !store.editingBlockId) {
				if (confirm('Remove this block? You can undo.')) {
					const sid = store.getSectionIdForBlock(store.selectedBlockId);
					if (sid) {
						store.removeBlock(sid, store.selectedBlockId);
					}
				}
				e.preventDefault();
			}
		}

		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});
</script>

{#if !ready || !store.document}
	<p class="p-8 text-slate-600">Loading lesson…</p>
{:else}
	<AppShell document={store.document} {store} />
{/if}

<script lang="ts">
	import { browser } from '$app/environment';
	import { onMount } from 'svelte';
	import { basePresetMap, LectioThemeSurface } from 'lectio';
	import type { LessonDocument } from 'lectio';
	import BlockCanvas from '$lib/builder/components/canvas/BlockCanvas.svelte';
	import CanvasOutline from '$lib/builder/components/canvas/CanvasOutline.svelte';
	import PaletteSidebar from '$lib/builder/components/palette/PaletteSidebar.svelte';
	import DocumentToolbar from '$lib/builder/components/toolbar/DocumentToolbar.svelte';
	import MediaManager from '$lib/builder/components/media/MediaManager.svelte';
	import VersionPanel from '$lib/builder/components/versions/VersionPanel.svelte';
	import OfflineSyncHooks from '$lib/builder/components/shell/OfflineSyncHooks.svelte';
	import { saveVersionSnapshot } from '$lib/builder/persistence/idb-store';
	import type { DocumentStore } from '$lib/builder/stores/document.svelte';

	let { document, store }: { document: LessonDocument; store: DocumentStore } = $props();

	const preset = $derived(basePresetMap[document.preset_id] ?? null);

	let paletteCollapsed = $state(false);
	let mobilePaletteOpen = $state(false);
	let mediaManagerOpen = $state(false);
	let versionPanelOpen = $state(false);

	/** Mutable refs for 30-minute auto-version (avoid stale interval closure). */
	const va = { docId: '', lastM: 0, lastA: 0 };

	$effect(() => {
		const d = store.document;
		if (!d) return;
		if (va.docId !== d.id) {
			va.docId = d.id;
			va.lastA = Date.now();
			va.lastM = Date.now();
			return;
		}
		void d.updated_at;
		va.lastM = Date.now();
	});

	onMount(() => {
		if (!browser || typeof indexedDB === 'undefined') return;
		const THIRTY_MS = 30 * 60 * 1000;
		const id = setInterval(() => {
			const d = store.document;
			if (!d) return;
			const now = Date.now();
			if (now - va.lastA < THIRTY_MS) return;
			if (va.lastM <= va.lastA) return;
			void saveVersionSnapshot(d.id, d, 'Auto-saved version').then(() => {
				va.lastA = Date.now();
			});
		}, 60_000);
		return () => clearInterval(id);
	});
</script>

<div class="builder-shell flex min-h-screen flex-col bg-slate-100">
	<OfflineSyncHooks />
	<DocumentToolbar
		document={store.document ?? document}
		saveStatus={store.saveStatus}
		onOpenMedia={() => (mediaManagerOpen = true)}
		onOpenHistory={() => (versionPanelOpen = true)}
	/>
	<div
		class="palette-toggle-bar hidden border-b border-slate-200 bg-white px-3 py-1.5 lg:flex lg:items-center lg:gap-2"
	>
		<button
			type="button"
			class="rounded-md border border-slate-300 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
			onclick={() => (paletteCollapsed = !paletteCollapsed)}
		>
			{paletteCollapsed ? 'Show palette' : 'Hide palette'}
		</button>
	</div>
	<div class="flex flex-1 overflow-hidden">
		{#if !paletteCollapsed}
			<div class="hidden shrink-0 lg:block">
				<PaletteSidebar {store} />
			</div>
		{:else}
			<div
				class="palette-sidebar hidden w-9 shrink-0 border-r border-slate-200 bg-white lg:flex lg:flex-col lg:items-center lg:pt-2"
			>
				<button
					type="button"
					class="rounded p-1 text-slate-600 hover:bg-slate-100"
					title="Show palette"
					aria-label="Show palette"
					onclick={() => (paletteCollapsed = false)}
				>
					>
				</button>
			</div>
		{/if}
		<main class="builder-main min-w-0 flex-1 overflow-y-auto p-6" data-testid="builder-main">
			{#if preset}
				<LectioThemeSurface {preset}>
					{#snippet children()}
						<BlockCanvas {store} />
					{/snippet}
				</LectioThemeSurface>
			{:else}
				<p class="text-sm text-amber-800">Unknown preset "{document.preset_id}" - showing unstyled canvas.</p>
				<BlockCanvas {store} />
			{/if}
		</main>
		<CanvasOutline {store} />
	</div>
</div>

{#if mediaManagerOpen}
	<MediaManager {store} onclose={() => (mediaManagerOpen = false)} />
{/if}

{#if store.document}
	<VersionPanel bind:open={versionPanelOpen} document={store.document} {store} />
{/if}

<button
	type="button"
	class="mobile-palette-fab fixed bottom-4 left-4 z-40 flex h-12 w-12 items-center justify-center rounded-full bg-blue-600 text-2xl font-light text-white shadow-lg lg:hidden"
	aria-label="Open component palette"
	onclick={() => (mobilePaletteOpen = true)}
>
	+
</button>

{#if mobilePaletteOpen}
	<div
		class="fixed inset-0 z-50 flex flex-col justify-end bg-black/40 lg:hidden"
		role="button"
		tabindex="-1"
		onclick={() => (mobilePaletteOpen = false)}
		onkeydown={(e) => e.key === 'Escape' && (mobilePaletteOpen = false)}
	>
		<div
			class="max-h-[min(70vh,32rem)] overflow-hidden rounded-t-xl bg-white shadow-xl"
			role="dialog"
			aria-label="Component palette"
			tabindex="-1"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
		>
			<div class="flex items-center justify-between border-b border-slate-200 px-3 py-2">
				<span class="text-sm font-semibold text-slate-800">Components</span>
				<button
					type="button"
					class="rounded-md px-2 py-1 text-sm text-blue-600 hover:bg-blue-50"
					onclick={() => (mobilePaletteOpen = false)}
				>
					Close
				</button>
			</div>
			<div class="max-h-[min(60vh,28rem)] overflow-y-auto">
				<PaletteSidebar {store} sheet />
			</div>
		</div>
	</div>
{/if}

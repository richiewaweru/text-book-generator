<script lang="ts">
	import { page } from '$app/state';
	import TextbookViewer from '$lib/components/TextbookViewer.svelte';

	const textbookId = $derived(page.params.id);

	// TODO: Fetch textbook HTML from backend when implemented
	let html = $state('<p>Textbook viewer — not yet implemented</p>');
</script>

<h1>Textbook: {textbookId}</h1>
<TextbookViewer {html} />

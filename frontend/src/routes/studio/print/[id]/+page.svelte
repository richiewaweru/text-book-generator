<!-- Temporary smoke page for V3 PDF / Playwright diagnostics; restore real print UI after tracing. -->
<script lang="ts">
	import { page } from '$app/state';

	const generationId = $derived(page.params.id);
</script>

<svelte:head>
	<title>Studio print smoke</title>
</svelte:head>

<div
	data-generation-complete="true"
	data-print-route="studio-print-smoke"
	data-generation-id={generationId}
>
	<h1>V3 Print Smoke Test</h1>
	<p>Generation: {generationId}</p>
</div>

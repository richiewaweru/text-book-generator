<script lang="ts">
	export let document: { title?: string } | null = null;
</script>

<div data-testid="mock-app-shell">Builder shell: {document?.title ?? 'Untitled lesson'}</div>

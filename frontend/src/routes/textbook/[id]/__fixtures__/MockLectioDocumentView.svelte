<script lang="ts">
	export let document: { subject?: string } | null = null;
</script>

<div data-testid="mock-document-view">{document?.subject ?? 'document'}</div>

<script lang="ts">
	import type { GenerationStatus } from '$lib/types';

	interface Props {
		status: GenerationStatus;
	}

	let { status }: Props = $props();
</script>

<div class="progress">
	<p>Status: <strong>{status.status}</strong></p>

	{#if status.progress}
		<p>Current: {status.progress.current_node}</p>
		<p>
			{status.progress.completed_nodes.length} / {status.progress.total_nodes} nodes complete
		</p>
	{/if}

	{#if status.error}
		<p class="error">{status.error}</p>
	{/if}
</div>

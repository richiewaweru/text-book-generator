<script lang="ts">
	import type { CanvasSection } from '$lib/types/v3';

	let { sections }: { sections: CanvasSection[] } = $props();

	function safeJson(value: unknown): string {
		try {
			return JSON.stringify(value, null, 2);
		} catch {
			return '[Unserializable section payload]';
		}
	}
</script>

<div class="v3-print-document">
	<h1>V3 Print Payload Test</h1>

	{#each sections as section, index}
		<section class="print-section">
			<h2>{index + 1}. {section.title}</h2>

			<p class="section-id">Section ID: {section.id}</p>

			<pre>{safeJson(section.mergedFields)}</pre>
		</section>
	{/each}
</div>

<style>
	.v3-print-document {
		font-family: Georgia, 'Times New Roman', serif;
		padding: 24px;
		color: #111;
		background: #fff;
	}

	h1 {
		margin: 0 0 24px;
		font-size: 28px;
	}

	.print-section {
		page-break-inside: avoid;
		margin-bottom: 32px;
		border-bottom: 1px solid #ddd;
		padding-bottom: 24px;
	}

	h2 {
		margin: 0 0 8px;
		font-size: 20px;
	}

	.section-id {
		margin: 0 0 12px;
		font-size: 12px;
		color: #555;
	}

	pre {
		white-space: pre-wrap;
		word-break: break-word;
		font-size: 11px;
		line-height: 1.4;
		background: #f6f6f6;
		border: 1px solid #ddd;
		border-radius: 8px;
		padding: 12px;
	}
</style>

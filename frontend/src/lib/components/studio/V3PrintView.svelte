<script lang="ts">
	import { blocksForSection } from '$lib/studio/v3-print-fields';
	import type { CanvasSection } from '$lib/types/v3';

	let { sections, subject = '' }: { sections: CanvasSection[]; subject?: string } = $props();

	const documentTitle = $derived(subject?.trim() || 'Lesson');
</script>

<div class="v3-print-document">
	<h1>{documentTitle}</h1>

	{#each sections as section, index}
		<section class="print-section">
			<h2>{index + 1}. {section.title}</h2>

			{#each blocksForSection(section) as block, bi (block.kind + '-' + bi + '-' + section.id)}
				{#if block.kind === 'h3'}
					<h3>{block.text}</h3>
				{:else if block.kind === 'p'}
					<p>{block.text}</p>
				{:else if block.kind === 'ul'}
					<ul class="print-list">
						{#each block.items as item}
							<li>{item}</li>
						{/each}
					</ul>
				{:else if block.kind === 'img'}
					<figure class="print-figure">
						<img src={block.src} alt={block.alt} class="print-img" />
					</figure>
				{/if}
			{/each}
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
		margin: 0 0 12px;
		font-size: 20px;
	}

	h3 {
		margin: 16px 0 8px;
		font-size: 16px;
		font-weight: 600;
	}

	p {
		margin: 0 0 10px;
		line-height: 1.5;
		font-size: 14px;
	}

	.print-list {
		margin: 0 0 12px;
		padding-left: 1.25rem;
		line-height: 1.5;
		font-size: 14px;
	}

	.print-figure {
		margin: 12px 0;
	}

	.print-img {
		max-width: 100%;
		height: auto;
		display: block;
	}
</style>

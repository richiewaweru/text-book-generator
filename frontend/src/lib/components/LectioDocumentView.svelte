<script lang="ts">
	import { LectioThemeSurface, basePresetMap, templateRegistryMap } from 'lectio';
	import type { GenerationDocument } from '$lib/types';

	interface Props {
		document: GenerationDocument;
	}

	let { document }: Props = $props();

	const template = $derived(templateRegistryMap[document.template_id]);
	const preset = $derived(basePresetMap[document.preset_id] ?? null);
</script>

{#if template}
	<LectioThemeSurface {preset}>
		<div class="page-frame space-y-6">
			<header class="lesson-shell p-6 sm:p-8">
				<div class="relative z-10 flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
					<div class="space-y-3">
						<p class="eyebrow">{preset?.name ?? document.preset_id}</p>
						<h2 class="text-3xl font-serif text-primary sm:text-4xl">{document.subject}</h2>
						<p class="max-w-3xl text-base leading-7 text-muted-foreground sm:text-lg sm:leading-8">
							{document.context}
						</p>
					</div>

					<div class="document-meta">
						<span>{template.contract.name}</span>
						<span>{document.mode.toUpperCase()}</span>
						<span>{document.sections.length} sections</span>
					</div>
				</div>
			</header>

			<div class="section-stack">
				{#each document.sections as section (section.section_id)}
					{@const TemplateRender = template.render}
					<article class="animate-step-reveal">
						<TemplateRender {section} />
					</article>
				{/each}
			</div>
		</div>
	</LectioThemeSurface>
{:else}
	<p>Unknown Lectio template: {document.template_id}</p>
{/if}

<style>
	.document-meta {
		display: grid;
		gap: 0.55rem;
		align-content: start;
		justify-items: start;
	}

	.document-meta span {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 0.45rem 0.75rem;
		border-radius: 999px;
		border: 1px solid color-mix(in srgb, var(--border) 72%, transparent);
		background: color-mix(in srgb, var(--secondary) 78%, white 22%);
		color: color-mix(in srgb, var(--foreground) 82%, white 18%);
		font-size: 0.82rem;
		font-weight: 600;
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}

	.section-stack {
		display: grid;
		gap: 1.25rem;
	}

	@media (min-width: 1024px) {
		.document-meta {
			justify-items: end;
		}
	}
</style>

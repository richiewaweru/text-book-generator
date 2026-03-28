<script lang="ts">
	import { LectioThemeSurface, basePresetMap, templateRegistryMap } from 'lectio';
	import { buildSectionSlots, type ViewerSectionSlot } from '$lib/generation/viewer-state';
	import type { GenerationDocument } from '$lib/types';

	interface Props {
		document: GenerationDocument;
		sectionSlots?: ViewerSectionSlot[];
		/** When set and `document.status === 'completed'`, shows "Export for Builder" in the lesson header. */
		onExportForBuilder?: () => void;
	}

	let { document, sectionSlots = undefined, onExportForBuilder = undefined }: Props = $props();

	const showExportForBuilder = $derived(
		document.status === 'completed' && typeof onExportForBuilder === 'function'
	);

	const template = $derived(templateRegistryMap[document.template_id]);
	const preset = $derived(basePresetMap[document.preset_id] ?? null);
	const resolvedSectionSlots = $derived(
		sectionSlots ?? buildSectionSlots(document, document.section_manifest.length || document.sections.length)
	);
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

					<div class="lesson-header-actions">
						{#if showExportForBuilder}
							<button
								type="button"
								class="export-builder-btn"
								onclick={() => onExportForBuilder?.()}
							>
								Export for Builder
							</button>
						{/if}
						<div class="document-meta">
							<span>{template.contract.name}</span>
							<span>{resolvedSectionSlots.length} sections</span>
						</div>
					</div>
				</div>
			</header>

			<div class="section-stack">
				{#each resolvedSectionSlots as slot (slot.section_id)}
					{#if slot.status === 'ready' && slot.section}
						{@const TemplateRender = template.render}
						<article class="animate-step-reveal">
							<TemplateRender section={slot.section} />
						</article>
					{:else}
						<article class="glass-panel section-skeleton" aria-busy="true">
							<p class="skeleton-kicker">Generating section {slot.position}</p>
							<h3 class="skeleton-title">{slot.title}</h3>
							<div class="skeleton-line short"></div>
							<div class="skeleton-line"></div>
							<div class="skeleton-line"></div>
						</article>
					{/if}
				{/each}
			</div>
		</div>
	</LectioThemeSurface>
{:else}
	<p>Unknown Lectio template: {document.template_id}</p>
{/if}

<style>
	.lesson-header-actions {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 0.75rem;
	}

	@media (min-width: 1024px) {
		.lesson-header-actions {
			align-items: flex-end;
		}
	}

	.export-builder-btn {
		flex-shrink: 0;
		padding: 0.5rem 1rem;
		font-size: 0.9rem;
		font-weight: 600;
		color: #0f172a;
		background: #e2e8f0;
		border: 1px solid #cbd5e1;
		border-radius: 0.375rem;
		cursor: pointer;
	}

	.export-builder-btn:hover {
		background: #cbd5e1;
	}

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

	.section-skeleton {
		display: grid;
		gap: 0.8rem;
		padding: 1.25rem;
		border-radius: 1.5rem;
	}

	.skeleton-kicker {
		margin: 0;
		font-size: 0.78rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--accent);
	}

	.skeleton-title {
		margin: 0;
		font-size: 1.2rem;
		color: var(--foreground);
	}

	.skeleton-line {
		height: 0.8rem;
		border-radius: 999px;
		background: color-mix(in srgb, var(--secondary) 82%, white 18%);
	}

	.skeleton-line.short {
		width: 68%;
	}

	@media (min-width: 1024px) {
		.document-meta {
			justify-items: end;
		}
	}
</style>

<script lang="ts">
	import { LectioThemeSurface, basePresetMap, templateRegistryMap } from 'lectio';
	import type { SectionContent } from 'lectio';
	import type { BookletStatus, V3DraftPack } from '$lib/types/v3';

	interface Props {
		pack: V3DraftPack;
		status: BookletStatus;
		issues?: Array<Record<string, unknown>>;
	}

	let { pack, status, issues = [] }: Props = $props();

	const template = $derived(templateRegistryMap[pack.template_id]);
	const preset = $derived(basePresetMap['blue-classroom'] ?? Object.values(basePresetMap)[0]);

	const labelByStatus: Record<BookletStatus, string> = {
		streaming_preview: 'Writing lesson pieces...',
		draft_ready: 'Draft booklet ready - checking consistency.',
		draft_with_warnings: 'Draft booklet available with warnings.',
		draft_needs_review: 'Draft needs review before classroom use.',
		final_ready: 'Final booklet ready.',
		final_with_warnings: 'Final booklet ready with minor warnings.',
		failed_unusable: 'No usable booklet could be assembled.'
	};
</script>

<section class="mx-auto max-w-4xl space-y-4 px-4 py-4">
	<p class="rounded-lg border border-border/60 bg-muted/30 px-4 py-3 text-sm font-medium">
		{labelByStatus[status]}
	</p>

	{#if pack.warnings.length}
		<div class="rounded-lg border border-amber-300/60 bg-amber-50/60 px-4 py-3 text-sm">
			<p class="font-semibold">Warnings</p>
			<ul class="ml-5 list-disc">
				{#each pack.warnings as warning}
					<li>{warning}</li>
				{/each}
			</ul>
		</div>
	{/if}

	{#if issues.length}
		<div class="rounded-lg border border-border/60 bg-card px-4 py-3 text-sm">
			<p class="font-semibold">Issues to review</p>
			<ul class="ml-5 list-disc">
				{#each issues as issue}
					<li>{String(issue.message ?? 'Unknown issue')}</li>
				{/each}
			</ul>
		</div>
	{/if}

	{#if template && preset}
		<LectioThemeSurface {preset}>
			<div class="space-y-6">
				{#each pack.sections as section, idx (String(section.section_id ?? idx))}
					{@const TemplateRender = template.render}
					<article class="rounded-xl border border-border/50 bg-card p-4 shadow-sm">
						<TemplateRender section={section as unknown as SectionContent} />
					</article>
				{/each}
			</div>
		</LectioThemeSurface>
	{:else}
		<p class="text-sm text-muted-foreground">
			Template unavailable for <code>{pack.template_id}</code>.
		</p>
	{/if}
</section>

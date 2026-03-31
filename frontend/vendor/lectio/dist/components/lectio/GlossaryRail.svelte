<script lang="ts">
	import type { GlossaryContent } from '../../types';
	import { Card } from '../ui/card';
	import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '../ui/collapsible';
	import { ScrollArea } from '../ui/scroll-area';
	import { cn } from '../../utils';

	let {
		content,
		class: className,
		mode = 'sticky'
	}: { content: GlossaryContent; class?: string; mode?: 'sticky' | 'drawer' | 'inline-strip' } =
		$props();
</script>

{#snippet glossaryTerms()}
	<ul class="space-y-3">
		{#each content.terms as term}
			<li class="rounded-[1.25rem] border border-white/12 bg-white/[0.12] p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
				<div class="text-sm font-semibold text-primary-foreground">{term.term}</div>
				<div class="text-xs leading-relaxed text-primary-foreground/94">{term.definition}</div>
				{#if term.used_in}
					<div class="mt-1 text-xs text-primary-foreground/84">Used in: {term.used_in}</div>
				{/if}
				{#if term.related?.length}
					<div class="mt-1 text-xs text-primary-foreground/84">
						See also: {term.related.join(', ')}
					</div>
				{/if}
			</li>
		{/each}
	</ul>
{/snippet}

{#if mode === 'inline-strip'}
	<Card class={cn('bg-primary text-primary-foreground p-4', className)}>
		<div class="space-y-3">
			<div class="space-y-2">
				<p class="eyebrow text-primary-foreground">Glossary strip</p>
				<p class="text-sm leading-6 text-primary-foreground/90">
					Key terms stay in the main flow instead of competing from the side.
				</p>
			</div>
			<div class="flex flex-wrap gap-3">
				{#each content.terms as term}
					<div class="min-w-[11rem] rounded-[1.1rem] border border-white/10 bg-white/8 px-4 py-3">
						<p class="text-xs font-semibold uppercase tracking-[0.18em] text-primary-foreground">
							{term.term}
						</p>
						<p class="mt-1 text-sm leading-6 text-primary-foreground/84">{term.definition}</p>
					</div>
				{/each}
			</div>
		</div>
	</Card>
{:else if mode === 'drawer'}
	<Card class={cn('bg-primary text-primary-foreground p-4', className)}>
		<div class="space-y-3">
			<div class="space-y-2">
				<p class="eyebrow text-primary-foreground">Glossary drawer</p>
				<p class="text-sm leading-6 text-primary-foreground/90">
					Open vocabulary support only when it is needed.
				</p>
			</div>
			<Collapsible>
				<CollapsibleTrigger
					class="inline-flex h-10 items-center justify-center rounded-xl bg-white/12 px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-white/18"
				>
					Show key terms
				</CollapsibleTrigger>
				<CollapsibleContent class="mt-4">
					<ScrollArea class="h-[18rem] pr-4">
						{@render glossaryTerms()}
					</ScrollArea>
				</CollapsibleContent>
			</Collapsible>
		</div>
	</Card>
{:else}
	<Card
		class={cn(
			'relative overflow-hidden rounded-[2rem] border border-primary/20 bg-primary text-primary-foreground shadow-[var(--shadow-warm)]',
			className
		)}
	>
		<div
			class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.16),transparent_34%),linear-gradient(180deg,rgba(255,255,255,0.06),transparent_52%)]"
		></div>
		<div
			class="pointer-events-none absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(rgba(255,255,255,0.04)_1px,transparent_1px)] bg-[length:24px_24px] [mask-image:linear-gradient(to_bottom,rgba(0,0,0,0.22),transparent_55%)]"
		></div>

		<div class="relative z-10 p-4">
			<div class="mb-3 space-y-2">
				<p class="eyebrow text-primary-foreground">Key terms</p>
				<p class="text-sm leading-6 text-primary-foreground/90">
					Vocabulary that should stay available while the learner moves through the section.
				</p>
			</div>

			<ScrollArea class="h-[18rem] lg:h-[28rem]">
				{@render glossaryTerms()}
			</ScrollArea>
		</div>
	</Card>
{/if}

<script lang="ts">
	import type { DiagramContent } from '../../types';
	import { Card } from '../ui/card';
	import { Popover, PopoverTrigger, PopoverContent } from '../ui/popover';
	import {
		Dialog,
		DialogPortal,
		DialogTrigger,
		DialogContent,
		DialogTitle,
		DialogOverlay
	} from '../ui/dialog';
	import { ZoomIn } from 'lucide-svelte';

	let { content }: { content: DiagramContent } = $props();

	type DiagramCallout = NonNullable<DiagramContent['callouts']>[number];
	const hasImage = $derived(Boolean(content.image_url?.trim()));
	const hasSvg = $derived(Boolean(content.svg_content?.trim()));
	const showCallouts = $derived(Boolean(!hasImage && hasSvg && content.callouts?.length));

	function getMarkerPosition(callout: DiagramCallout) {
		const horizontalOffset = callout.x >= 72 ? -20 : callout.x <= 28 ? 20 : 0;
		const verticalOffset = callout.y >= 72 ? -20 : callout.y <= 28 ? 20 : -18;

		return {
			left: `calc(${callout.x}% ${horizontalOffset >= 0 ? '+' : '-'} ${Math.abs(horizontalOffset)}px)`,
			top: `calc(${callout.y}% ${verticalOffset >= 0 ? '+' : '-'} ${Math.abs(verticalOffset)}px)`
		};
	}
</script>

<div class="diagram-block-root">
<Card class="border-primary/10 bg-white/88 p-6">
	<div class="space-y-4">
		<div class="flex flex-wrap items-center gap-3">
			<p class="eyebrow">Diagram</p>
			{#if content.figure_number}
				<span class="rounded-full border border-border/70 bg-secondary px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-foreground/75">
					Figure {content.figure_number}
				</span>
			{/if}
		</div>

		<Dialog>
			<DialogTrigger>
				<div class="group relative cursor-pointer" role="img" aria-label={content.alt_text}>
					<div class="overflow-hidden rounded-[1.25rem] border border-border/70 bg-white shadow-[inset_0_1px_0_rgba(255,255,255,0.72)] [&_svg]:h-auto [&_svg]:w-full">
						{#if hasImage}
							<img src={content.image_url} alt="" class="h-auto w-full" />
						{:else if hasSvg}
							{@html content.svg_content}
						{:else}
							<div class="flex min-h-48 items-center justify-center p-6 text-sm text-muted-foreground">
								Diagram source unavailable.
							</div>
						{/if}
					</div>

					{#if showCallouts}
						{#each content.callouts as callout, index}
							{@const markerPosition = getMarkerPosition(callout)}
							<div
								class="pointer-events-none absolute h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/90 bg-primary shadow-[0_3px_10px_rgba(15,23,42,0.18)] diagram-block-dot"
								style="left: {callout.x}%; top: {callout.y}%;"
							></div>
							<Popover>
								<PopoverTrigger>
									{#snippet child({ props })}
										<button
											{...props}
											type="button"
											class="absolute flex h-7 w-7 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-white/85 bg-primary text-[11px] font-semibold text-primary-foreground shadow-[0_10px_24px_rgba(15,23,42,0.18)] transition-transform hover:-translate-y-[55%] hover:scale-[1.04] diagram-block-callout-btn"
											style="left: {markerPosition.left}; top: {markerPosition.top};"
											aria-label={callout.label}
											onpointerdown={(event) => event.stopPropagation()}
											onclick={(event) => event.stopPropagation()}
										>
											{index + 1}
										</button>
									{/snippet}
								</PopoverTrigger>
								<PopoverContent class="glass-panel w-64 rounded-[1.1rem] p-3 text-sm leading-6 text-foreground/82">
									<div class="relative z-10 space-y-2">
										<div class="flex items-start gap-3">
											<span
												class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-[11px] font-semibold text-primary-foreground"
											>
												{index + 1}
											</span>
											<div>
												<p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary/70">
													Diagram point
												</p>
												<p class="text-sm font-semibold text-foreground">{callout.label}</p>
											</div>
										</div>
										<p class="text-sm leading-6 text-foreground/80">
											{callout.explanation}
										</p>
									</div>
								</PopoverContent>
							</Popover>
						{/each}
					{/if}

					<div class="absolute right-3 top-3 rounded-full bg-white/82 p-1.5 opacity-0 shadow-sm backdrop-blur-sm transition-opacity group-hover:opacity-100 diagram-block-zoom">
						<ZoomIn class="h-4 w-4 text-muted-foreground" />
					</div>
				</div>
			</DialogTrigger>

			<DialogPortal>
				<DialogOverlay class="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm" />
				<DialogContent
					class="glass-panel fixed left-1/2 top-1/2 z-50 max-h-[min(88vh,56rem)] w-[min(92vw,64rem)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-[1.75rem] p-6 animate-scale-in sm:p-7"
				>
					<div class="relative z-10 space-y-4">
						<DialogTitle class="text-base font-semibold text-primary">
							{content.zoom_label ?? 'Diagram detail'}
						</DialogTitle>
						<div
							class="overflow-hidden rounded-[1.25rem] border border-border/70 bg-white p-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.72)] [&_svg]:h-auto [&_svg]:w-full"
							role="img"
							aria-label={content.alt_text}
						>
							{#if hasImage}
								<img src={content.image_url} alt="" class="h-auto w-full" />
							{:else if hasSvg}
								{@html content.svg_content}
							{:else}
								<div class="flex min-h-64 items-center justify-center p-6 text-sm text-muted-foreground">
									Diagram source unavailable.
								</div>
							{/if}
						</div>
						<p class="text-sm leading-6 text-muted-foreground">{content.caption}</p>
					</div>
				</DialogContent>
			</DialogPortal>
		</Dialog>

		{#if showCallouts}
			<p class="text-xs leading-5 text-muted-foreground">
				Tap a numbered point to see the labeled detail for that part of the diagram.
			</p>
		{/if}

		<p class="text-sm leading-6 text-muted-foreground">{content.caption}</p>
	</div>
</Card>
</div>

<style>
	@media print {
		.diagram-block-root {
			page-break-inside: avoid;
		}

		/* Hide the zoom button overlay and callout interactive buttons */
		.diagram-block-zoom,
		.diagram-block-callout-btn,
		.diagram-block-dot {
			display: none !important;
		}
	}
</style>

<script lang="ts">
	import type { ExplanationContent } from '../../types';
	import { Card } from '../ui/card';
	import { renderBlockMarkdown } from '../../markdown';
	import { BookOpen, Lightbulb, Info, TriangleAlert, GraduationCap } from 'lucide-svelte';

	const calloutConfig = {
		remember: {
			label: 'Remember',
			className: 'border-blue-200 bg-blue-50/75 text-blue-800',
			icon: BookOpen
		},
		insight: {
			label: 'Key insight',
			className: 'border-violet-200 bg-violet-50/75 text-violet-800',
			icon: Lightbulb
		},
		sidenote: {
			label: 'Side note',
			className: 'border-gray-200 bg-gray-50/75 text-gray-700',
			icon: Info
		},
		warning: {
			label: 'Warning',
			className: 'border-amber-200 bg-amber-50/75 text-amber-800',
			icon: TriangleAlert
		},
		'exam-tip': {
			label: 'Exam tip',
			className: 'border-emerald-200 bg-emerald-50/75 text-emerald-800',
			icon: GraduationCap
		}
	};

	let { content }: { content: ExplanationContent } = $props();

	function escapeHtml(str: string): string {
		return str
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;')
			.replace(/'/g, '&#39;');
	}

	function highlightEmphasis(text: string, phrases: string[]): string {
		let result = escapeHtml(text);
		for (const phrase of phrases) {
			const escaped = phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
			result = result.replace(
				new RegExp(escaped, 'gi'),
				(match) => `<mark class="lectio-emphasis">${match}</mark>`
			);
		}
		return result;
	}

	function renderBody(body: string, phrases: string[]): string {
		// renderBlockMarkdown escapes HTML internally, so we apply emphasis on the HTML output directly
		let result = renderBlockMarkdown(body);
		for (const phrase of phrases) {
			const escaped = phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
			result = result.replace(
				new RegExp(escaped, 'gi'),
				(match) => `<mark class="lectio-emphasis">${match}</mark>`
			);
		}
		return result;
	}
</script>

<Card class="border-primary/10 bg-white/88 p-6">
	<div class="space-y-4">
		<div class="space-y-2">
			<p class="eyebrow text-blue-600">Explanation</p>
			<p class="text-base leading-7 text-foreground/84 prose prose-sm max-w-none">
				{@html renderBody(content.body, content.emphasis)}
			</p>
		</div>

		{#if content.callouts?.length}
			<div class="space-y-3">
				{#each content.callouts as callout}
					{@const cfg = calloutConfig[callout.type]}
					<div class="flex gap-3 rounded-xl border p-3 text-sm leading-6 {cfg.className}">
						<cfg.icon class="mt-0.5 h-4 w-4 shrink-0" />
						<div>
							<span class="font-semibold">{cfg.label}:</span>
							{callout.text}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</Card>

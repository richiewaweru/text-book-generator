<script lang="ts">
	import type { CalloutBlockContent } from '../../types';
	import { Alert, AlertTitle, AlertDescription } from '../ui/alert';
	import { Info, Lightbulb, TriangleAlert, GraduationCap, BookOpen } from 'lucide-svelte';

	let { content }: { content: CalloutBlockContent } = $props();

	const variantStyles: Record<string, string> = {
		info: 'border-blue-200 bg-blue-50/60',
		tip: 'border-emerald-200 bg-emerald-50/60',
		warning: 'border-amber-200 bg-amber-50/60',
		'exam-tip': 'border-violet-200 bg-violet-50/60',
		remember: 'border-rose-200 bg-rose-50/60'
	};

	const variantIconColor: Record<string, string> = {
		info: 'text-blue-500',
		tip: 'text-emerald-500',
		warning: 'text-amber-500',
		'exam-tip': 'text-violet-500',
		remember: 'text-rose-500'
	};

	const variantTitleColor: Record<string, string> = {
		info: 'text-blue-700',
		tip: 'text-emerald-700',
		warning: 'text-amber-700',
		'exam-tip': 'text-violet-700',
		remember: 'text-rose-700'
	};

	const icons = { info: Info, tip: Lightbulb, warning: TriangleAlert, 'exam-tip': GraduationCap, remember: BookOpen };
	const Icon = $derived(icons[content.variant] ?? Info);
</script>

<Alert class={variantStyles[content.variant] ?? variantStyles.info}>
	<Icon class="h-4 w-4 {variantIconColor[content.variant] ?? variantIconColor.info}" />
	{#if content.heading}
		<AlertTitle class="{variantTitleColor[content.variant] ?? variantTitleColor.info} text-sm font-semibold">
			{content.heading}
		</AlertTitle>
	{/if}
	<AlertDescription class="mt-1 text-sm leading-relaxed">
		{content.body}
	</AlertDescription>
</Alert>

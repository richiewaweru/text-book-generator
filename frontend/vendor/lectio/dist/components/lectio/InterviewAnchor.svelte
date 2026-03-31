<script lang="ts">
	import type { InterviewContent } from '../../types';
	import { Card } from '../ui/card';
	import { MessageCircle } from 'lucide-svelte';

	let { content }: { content: InterviewContent } = $props();
</script>

<Card class="border-l-4 border-l-orange-400 bg-orange-50/50 p-6">
	<div class="flex gap-3">
		<MessageCircle class="mt-0.5 h-5 w-5 shrink-0 text-orange-500" />
		<div class="space-y-3">
			<div class="space-y-2">
				<p class="eyebrow text-orange-600">Explain it</p>
				<p class="text-sm leading-7 text-foreground">{content.prompt}</p>
				<p class="text-xs italic text-muted-foreground">Audience: {content.audience}</p>
			</div>

			{#if content.follow_up}
				<div class="border-t border-orange-200 pt-3">
					<p class="text-xs font-medium text-orange-600">Follow-up</p>
					<p class="mt-1 text-sm leading-relaxed text-foreground/80">{content.follow_up}</p>
				</div>
			{/if}
		</div>
	</div>
</Card>

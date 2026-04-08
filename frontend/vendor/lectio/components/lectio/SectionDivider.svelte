<script lang="ts">
	import type { SectionDividerContent } from '../../types';
	import { Separator } from '../ui/separator';

	let { content }: { content: SectionDividerContent } = $props();
</script>

<div class="flex items-center gap-4 py-2">
	<Separator class="flex-1" />
	<span class="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
		{content.label}
	</span>
	<Separator class="flex-1" />
</div>

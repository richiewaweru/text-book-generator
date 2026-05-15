<script lang="ts">
	import type { BlueprintPreviewDTO } from '$lib/types/v3';

	interface Props {
		blueprint: BlueprintPreviewDTO;
		onApprove: () => void;
		onAdjust: (instruction: string) => void;
		onCancel?: () => void;
		contextLabel?: string;
		approveLabel?: string;
		cancelLabel?: string;
		parentTitle?: string | null;
	}

	let {
		blueprint,
		onApprove,
		onAdjust,
		onCancel,
		contextLabel = 'Lesson plan',
		approveLabel = 'Approve and generate',
		cancelLabel = 'Back',
		parentTitle = null
	}: Props = $props();

	let adjustText = $state('');
	let showAdjust = $state(false);

	const PRESETS = [
		{
			label: 'Make it shorter',
			value: 'Reduce the number of sections and keep the resource concise.'
		},
		{
			label: 'Add more scaffolding',
			value: 'Add more scaffolding and worked examples for lower-confidence learners.'
		},
		{
			label: 'Fewer questions',
			value: 'Reduce the number of practice questions while preserving the main concept check.'
		},
		{
			label: 'More visual',
			value: 'Add more visual supports and diagrams where appropriate.'
		}
	];

	const difficultyLabel: Record<string, string> = {
		warm: 'Warm',
		medium: 'Medium',
		cold: 'Cold',
		transfer: 'Transfer'
	};

	function applyPreset(value: string) {
		adjustText = value;
		showAdjust = true;
	}
</script>

<div class="mx-auto max-w-3xl space-y-8 px-4 py-10">
	<header class="flex flex-wrap items-start justify-between gap-4 border-b border-border/60 pb-6">
		<div>
			<p class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{contextLabel}</p>
			<h2 class="mt-1 text-3xl font-semibold">{blueprint.title}</h2>
			{#if parentTitle}
				<p class="mt-1 text-xs text-muted-foreground">Based on: {parentTitle}</p>
			{/if}
			<p class="mt-2 text-sm text-muted-foreground">{blueprint.register_summary}</p>
			{#if blueprint.learner_context}
				{@const lc = blueprint.learner_context}
				<div class="mt-3 flex flex-wrap gap-2">
					{#if lc.grade_level}
						<span class="rounded-full bg-muted px-3 py-1 text-xs font-medium">{lc.grade_level}</span>
					{/if}
					{#if lc.subject}
						<span class="rounded-full bg-muted px-3 py-1 text-xs font-medium">{lc.subject}</span>
					{/if}
					{#if lc.duration_minutes}
						<span class="rounded-full bg-muted px-3 py-1 text-xs font-medium">{lc.duration_minutes} min</span>
					{/if}
					{#if lc.learner_level && lc.learner_level !== 'on_grade'}
						<span class="rounded-full bg-muted px-3 py-1 text-xs font-medium capitalize">
							{lc.learner_level.replace(/_/g, ' ')}
						</span>
					{/if}
					{#if lc.language_support && lc.language_support !== 'none'}
						<span class="rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">
							{lc.language_support === 'some_ell' ? 'Some EAL' : 'Mostly EAL'}
						</span>
					{/if}
					{#each lc.support_needs as need}
						<span class="rounded-full bg-muted px-3 py-1 text-xs font-medium capitalize">
							{need.replace(/_/g, ' ')}
						</span>
					{/each}
				</div>
			{/if}
		</div>
		<span class="rounded-full bg-muted px-3 py-1 text-xs font-medium capitalize">
			{blueprint.resource_type.replace(/_/g, ' ')}
		</span>
	</header>

	{#if blueprint.support_summary.length}
		<section class="rounded-xl border border-border/60 bg-muted/30 p-4">
			<h3 class="text-sm font-semibold">Support cues</h3>
			<ul class="mt-2 list-inside list-disc text-sm text-muted-foreground">
				{#each blueprint.support_summary as line}
					<li>{line}</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if blueprint.lenses.length}
		<section class="space-y-3">
			<h3 class="text-lg font-semibold">How we planned this</h3>
			<ul class="space-y-3">
				{#each blueprint.lenses as lens}
					<li class="rounded-xl border border-border/60 bg-card p-4 shadow-sm">
						<p class="font-semibold">{lens.label}</p>
						<p class="text-sm text-muted-foreground">{lens.reason}</p>
						{#if lens.effects.length}
							<ul class="mt-2 list-inside list-disc text-sm">
								{#each lens.effects as effect}
									<li>{effect}</li>
								{/each}
							</ul>
						{/if}
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if blueprint.anchor}
		<section class="space-y-3">
			<h3 class="text-lg font-semibold">Anchor</h3>
			<div class="rounded-xl border border-border/60 bg-card p-4">
				<p class="font-semibold">{blueprint.anchor.label}</p>
				<dl class="mt-3 grid gap-2 text-sm">
					{#each Object.entries(blueprint.anchor.facts) as [key, val]}
						<div>
							<dt class="text-muted-foreground">{key.replace(/_/g, ' ')}</dt>
							<dd>{val}</dd>
						</div>
					{/each}
					{#if blueprint.anchor.correct_result}
						<div>
							<dt class="text-muted-foreground">Correct answer</dt>
							<dd>{blueprint.anchor.correct_result}</dd>
						</div>
					{/if}
				</dl>
				<p class="mt-3 text-xs text-muted-foreground">
					Reuse: {blueprint.anchor.reuse_scope.replace(/_/g, ' ')}
				</p>
			</div>
		</section>
	{/if}

	<section class="space-y-3">
		<h3 class="text-lg font-semibold">Lesson sections</h3>
		<ol class="space-y-4">
			{#each blueprint.section_plan as section}
				<li class="rounded-xl border border-border/60 bg-card p-4">
					<div class="flex flex-wrap items-baseline justify-between gap-2">
						<p class="font-semibold">{section.title}</p>
						<span class="text-xs text-muted-foreground">
							{section.components.map((c) => c.teacher_label).join(' · ')}
						</span>
					</div>
					<p class="mt-2 text-sm text-muted-foreground">{section.learning_intent}</p>
				</li>
			{/each}
		</ol>
	</section>

	{#if blueprint.question_plan.length}
		<section class="space-y-3">
			<h3 class="text-lg font-semibold">Practice questions</h3>
			<div class="overflow-x-auto rounded-xl border border-border/60">
				<table class="w-full text-left text-sm">
					<thead class="bg-muted/50 text-xs uppercase text-muted-foreground">
						<tr>
							<th class="px-3 py-2">Item</th>
							<th class="px-3 py-2">Difficulty</th>
							<th class="px-3 py-2">Diagram</th>
							<th class="px-3 py-2">Answer</th>
						</tr>
					</thead>
					<tbody>
						{#each blueprint.question_plan as q, i}
							<tr class="border-t border-border/40">
								<td class="px-3 py-2">Q{i + 1}</td>
								<td class="px-3 py-2 capitalize">{difficultyLabel[q.difficulty] ?? q.difficulty}</td>
								<td class="px-3 py-2">{q.diagram_required ? 'Yes' : '—'}</td>
								<td class="max-w-xs truncate px-3 py-2">{q.expected_answer}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</section>
	{/if}

	<div class="space-y-3 pt-4">
		<button
			type="button"
			class="w-full rounded-md bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
			onclick={onApprove}
		>
			{approveLabel}
		</button>

		{#if onCancel}
			<button
				type="button"
				class="w-full rounded-md border border-input px-4 py-3 text-sm font-semibold"
				onclick={onCancel}
			>
				{cancelLabel}
			</button>
		{/if}

		<div class="space-y-2">
			<p class="text-xs text-muted-foreground">Or adjust the plan first:</p>
			<div class="flex flex-wrap gap-2">
				{#each PRESETS as preset}
					<button
						type="button"
						class="rounded-full border border-input px-3 py-1.5 text-xs font-medium hover:bg-muted"
						onclick={() => applyPreset(preset.value)}
					>
						{preset.label}
					</button>
				{/each}
			</div>
		</div>

		{#if showAdjust}
			<div class="space-y-2 rounded-xl border border-border/60 bg-muted/20 p-4">
				<textarea
					class="min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
					bind:value={adjustText}
					placeholder="Describe what you want to change…"
				></textarea>
				<div class="flex gap-2">
					<button
						type="button"
						class="flex-1 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-50"
						disabled={adjustText.trim().length === 0}
						onclick={() => {
							onAdjust(adjustText.trim());
							adjustText = '';
							showAdjust = false;
						}}
					>
						Update plan
					</button>
					<button
						type="button"
						class="rounded-md border border-input px-4 py-2 text-sm"
						onclick={() => {
							showAdjust = false;
							adjustText = '';
						}}
					>
						Cancel
					</button>
				</div>
			</div>
		{:else}
			<button
				type="button"
				class="w-full rounded-md border border-input px-4 py-2 text-xs text-muted-foreground hover:bg-muted"
				onclick={() => (showAdjust = true)}
			>
				Write your own instruction
			</button>
		{/if}
	</div>
</div>

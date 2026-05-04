<script lang="ts">
	import type { V3InputForm } from '$lib/types/v3';

	interface Props {
		form: V3InputForm | null;
	}

	let { form }: Props = $props();

	const LESSON_MODE_LABELS: Record<string, string> = {
		first_exposure: 'First exposure',
		consolidation: 'Consolidation',
		repair: 'Repair',
		retrieval: 'Retrieval practice',
		transfer: 'Transfer',
		other: 'Other'
	};

	const LEVEL_LABELS: Record<string, string> = {
		below_grade: 'Below grade level',
		on_grade: 'At grade level',
		above_grade: 'Above grade level',
		mixed: 'Mixed ability'
	};

	const SUPPORT_LABELS: Record<string, string> = {
		visuals: 'Visual supports',
		step_by_step: 'Step-by-step scaffolding',
		vocabulary_support: 'Vocabulary support',
		worked_examples: 'Worked examples',
		simpler_reading: 'Simplified reading level',
		challenge: 'Challenge questions'
	};

	const messages = [
		'Thinking about your class…',
		'Planning the teaching sequence…',
		'Selecting the right components…',
		'Designing your practice questions…',
		'Almost there…'
	];

	let messageIndex = $state(0);

	$effect(() => {
		const interval = setInterval(() => {
			messageIndex = (messageIndex + 1) % messages.length;
		}, 8000);
		return () => clearInterval(interval);
	});
</script>

<div class="mx-auto max-w-xl space-y-8 px-4 py-16 text-center">
	<div class="flex justify-center">
		<div class="relative h-16 w-16">
			<div class="absolute inset-0 animate-ping rounded-full bg-primary/20"></div>
			<div class="absolute inset-2 rounded-full bg-primary/40"></div>
			<div class="absolute inset-4 rounded-full bg-primary"></div>
		</div>
	</div>

	<div class="space-y-1">
		<p class="text-lg font-medium transition-all duration-500">{messages[messageIndex]}</p>
		<p class="text-sm text-muted-foreground">Building your lesson plan</p>
	</div>

	{#if form}
		<div
			class="mx-auto max-w-sm rounded-xl border border-border/60 bg-muted/30 px-6 py-4 text-left space-y-2 text-sm"
		>
			<div class="flex justify-between">
				<span class="text-muted-foreground">Grade</span>
				<span class="font-medium">{form.grade_level}</span>
			</div>

			<div class="flex justify-between">
				<span class="text-muted-foreground">Subject</span>
				<span class="font-medium">{form.subject}</span>
			</div>

			<div class="flex justify-between">
				<span class="text-muted-foreground">Duration</span>
				<span class="font-medium">{form.duration_minutes} min</span>
			</div>

			{#if form.lesson_mode}
				<div class="flex justify-between">
					<span class="text-muted-foreground">Lesson type</span>
					<span class="font-medium">
						{LESSON_MODE_LABELS[form.lesson_mode] ?? form.lesson_mode}
					</span>
				</div>
			{/if}

			{#if form.learner_level}
				<div class="flex justify-between">
					<span class="text-muted-foreground">Learner level</span>
					<span class="font-medium">{LEVEL_LABELS[form.learner_level] ?? form.learner_level}</span>
				</div>
			{/if}

			{#if form.support_needs && form.support_needs.length > 0}
				<div class="flex justify-between">
					<span class="text-muted-foreground">Support</span>
					<span class="font-medium">
						{form.support_needs.map((s) => SUPPORT_LABELS[s] ?? s).join(', ')}
					</span>
				</div>
			{/if}

			{#if form.topic}
				<div class="border-t border-border/40 pt-2 mt-2">
					<p class="text-muted-foreground text-xs mb-1">Topic</p>
					<p class="text-sm leading-snug line-clamp-2">{form.topic}</p>
					{#if form.subtopics && form.subtopics.length > 0}
						<p class="mt-1 text-xs text-muted-foreground line-clamp-2">
							Subtopics: {form.subtopics.join(', ')}
						</p>
					{/if}
				</div>
			{/if}
		</div>
	{/if}
</div>


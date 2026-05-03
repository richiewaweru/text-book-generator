<script lang="ts">
	import type { V3InputForm } from '$lib/types/v3';

	interface Props {
		onSubmit: (form: V3InputForm) => void;
	}

	let { onSubmit }: Props = $props();

	let year_group = $state('');
	let subject = $state('');
	let duration_minutes = $state(50);
	let free_text = $state('');

	const YEAR_GROUPS = [
		'Year 1',
		'Year 2',
		'Year 3',
		'Year 4',
		'Year 5',
		'Year 6',
		'Year 7',
		'Year 8',
		'Year 9',
		'Year 10',
		'Year 11',
		'Year 12',
		'Grade 6',
		'Grade 7',
		'Grade 8',
		'Grade 9',
		'Grade 10',
		'Grade 11',
		'Grade 12'
	];

	const SUBJECTS = [
		'Mathematics',
		'English',
		'Science',
		'Physics',
		'Chemistry',
		'Biology',
		'History',
		'Geography',
		'Economics',
		'Computer Science',
		'Other'
	];

	const DURATIONS = [
		{ label: '30 min', value: 30 },
		{ label: '50 min', value: 50 },
		{ label: '60 min', value: 60 },
		{ label: '90 min', value: 90 }
	];

	const canSubmit = $derived(year_group !== '' && subject !== '' && free_text.trim().length > 20);

	function handleSubmit(e: Event) {
		e.preventDefault();
		if (!canSubmit) return;
		onSubmit({
			year_group,
			subject,
			duration_minutes: Number(duration_minutes),
			free_text: free_text.trim()
		});
	}
</script>

<div class="mx-auto max-w-xl space-y-6 px-4 py-10">
	<header class="space-y-2 text-center">
		<h1 class="text-3xl font-semibold tracking-tight">What do you want to teach?</h1>
		<p class="text-muted-foreground">Describe what you need and we will build the plan.</p>
	</header>

	<form class="space-y-5" onsubmit={handleSubmit}>
		<div class="grid gap-3 sm:grid-cols-3">
			<label class="grid gap-1 text-sm font-medium">
				<span>Year group</span>
				<select
					class="rounded-md border border-input bg-background px-3 py-2"
					bind:value={year_group}
					aria-label="Year group"
				>
					<option value="">Choose…</option>
					{#each YEAR_GROUPS as yg}
						<option value={yg}>{yg}</option>
					{/each}
				</select>
			</label>
			<label class="grid gap-1 text-sm font-medium">
				<span>Subject</span>
				<select
					class="rounded-md border border-input bg-background px-3 py-2"
					bind:value={subject}
					aria-label="Subject"
				>
					<option value="">Choose…</option>
					{#each SUBJECTS as s}
						<option value={s}>{s}</option>
					{/each}
				</select>
			</label>
			<label class="grid gap-1 text-sm font-medium">
				<span>Duration</span>
				<select
					class="rounded-md border border-input bg-background px-3 py-2"
					bind:value={duration_minutes}
					aria-label="Duration"
				>
					{#each DURATIONS as d}
						<option value={d.value}>{d.label}</option>
					{/each}
				</select>
			</label>
		</div>

		<label class="grid gap-1 text-sm font-medium">
			<span>Teaching intent</span>
			<textarea
				class="min-h-[140px] rounded-md border border-input bg-background px-3 py-2"
				bind:value={free_text}
				placeholder={`Describe what you want to teach and what learners should do.\nExample: Year 6 compound shapes — first time with L-shapes; some EAL learners.`}
				aria-label="Teaching intent"
			></textarea>
		</label>

		<button
			type="submit"
			disabled={!canSubmit}
			class="w-full rounded-md bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground disabled:opacity-50"
		>
			Continue
		</button>
	</form>
</div>

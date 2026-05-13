<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { isApiError } from '$lib/api/errors';
	import { listBuilderLessons, type BuilderLessonSummary } from '$lib/builder/api/lesson-crud';
	import { logout } from '$lib/stores/auth';

	let loading = $state(true);
	let errorMessage = $state<string | null>(null);
	let lessons = $state<BuilderLessonSummary[]>([]);

	function sourceTypeLabel(sourceType: BuilderLessonSummary['source_type']): string {
		if (sourceType === 'v3_generation') return 'From generation';
		if (sourceType === 'template') return 'Template';
		return 'Manual';
	}

	function sourceTypeTone(sourceType: BuilderLessonSummary['source_type']): string {
		if (sourceType === 'v3_generation') return 'bg-indigo-100 text-indigo-800';
		if (sourceType === 'template') return 'bg-emerald-100 text-emerald-800';
		return 'bg-slate-200 text-slate-700';
	}

	function formatUpdatedAt(value: string): string {
		const date = new Date(value);
		if (Number.isNaN(date.valueOf())) return value;
		return date.toLocaleString();
	}

	onMount(async () => {
		try {
			lessons = await listBuilderLessons();
		} catch (error) {
			if (isApiError(error) && error.status === 401) {
				logout();
				await goto('/login', { replaceState: true });
				return;
			}
			errorMessage = error instanceof Error ? error.message : 'Failed to load lessons.';
		} finally {
			loading = false;
		}
	});
</script>

<div class="mx-auto max-w-4xl p-6">
	<div class="mb-5 flex flex-wrap items-center justify-between gap-3">
		<div>
			<h1 class="text-2xl font-bold text-slate-900">Builder lessons</h1>
			<p class="text-sm text-slate-600">Open an editable lesson or start a new one.</p>
		</div>
		<a
			href="/builder/new"
			class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
			data-testid="builder-new-link"
		>
			New lesson
		</a>
	</div>

	{#if loading}
		<p class="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">Loading lessons...</p>
	{:else if errorMessage}
		<p class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
			{errorMessage}
		</p>
	{:else if lessons.length === 0}
		<div class="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-700">
			<p class="mb-3">No editable lessons yet.</p>
			<a
				href="/builder/new"
				class="inline-flex rounded-lg border border-slate-300 bg-white px-3 py-1.5 font-semibold text-slate-800 hover:bg-slate-50"
			>
				Create your first lesson
			</a>
		</div>
	{:else}
		<ul class="grid gap-3">
			{#each lessons as lesson (lesson.id)}
				<li class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
					<div class="flex flex-wrap items-start justify-between gap-2">
						<div class="min-w-0">
							<a
								href={`/builder/${lesson.id}`}
								class="line-clamp-2 text-base font-semibold text-blue-700 hover:text-blue-900 hover:underline"
							>
								{lesson.title}
							</a>
							<p class="mt-1 text-xs text-slate-500">Updated {formatUpdatedAt(lesson.updated_at)}</p>
						</div>
						<span
							class={`rounded-full px-2.5 py-1 text-xs font-semibold ${sourceTypeTone(lesson.source_type)}`}
						>
							{sourceTypeLabel(lesson.source_type)}
						</span>
					</div>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import {
		approveLessonGeneration,
		getLessonGenerationProgress,
		reviewLessonGeneration,
		openLessonInBuilder,
		retryLessonGeneration,
		type LessonGenerationProgress,
		type LessonGenerationReview as Review
	} from '$lib/api/units';

	let { unitId, lessonId, generationId, pathVersionId, pathRevision, initialStage, initialBuilderId } = $props<{
		unitId: string;
		lessonId: string;
		generationId: string;
		pathVersionId: string;
		pathRevision: number;
		initialStage?: string;
		initialBuilderId?: string | null;
	}>();

	let review = $state<Review | null>(null);
	let progress = $state<LessonGenerationProgress | null>(null);
	let error = $state<string | null>(null);
	let busy = $state<'loading' | 'approving' | 'retrying' | 'opening' | null>(null);
	let timer: ReturnType<typeof setInterval> | null = null;
	let pollInFlight = false;
	let opened = $state(false);
	let generationInitiated = $state(false);

	function stage(value: string | undefined): 'awaiting_review' | 'running' | 'partial' | 'failed' | 'complete' {
		const normalized = (value ?? '').toLowerCase();
		if (normalized.includes('fail') || normalized.includes('error') || normalized === 'assembly_blocked') return 'failed';
		if (normalized.includes('complete') || normalized === 'ready') return 'complete';
		if (normalized.includes('partial') || normalized.includes('block')) return 'partial';
		if (normalized.includes('run') || normalized.includes('generat') || normalized.includes('progress')) return 'running';
		return 'awaiting_review';
	}

	const currentStage = $derived.by(() => {
		const fetched = stage(progress?.stage ?? review?.stage);
		// The prepared-status response is the page's authoritative snapshot. If
		// it already proves a completed document, do not let a stale review
		// response reopen the approval card during hydration.
		return stage(initialStage) === 'complete' && fetched !== 'failed' ? 'complete' : fetched;
	});
	const retryable = $derived(progress?.retryable ?? review?.retryable ?? false);
	const resolvedBuilderId = $derived(progress?.builder_id ?? review?.builder_id ?? initialBuilderId ?? null);

	function stopPolling(): void {
		if (timer) clearInterval(timer);
		timer = null;
	}

	function startPolling(): void {
		if (timer) return;
		timer = setInterval(() => void poll(), 4000);
	}

	async function openBuilder(): Promise<void> {
		if (opened || busy === 'opening') return;
		opened = true;
		busy = 'opening';
		try {
			const result = resolvedBuilderId
				? { builder_id: resolvedBuilderId }
				: await openLessonInBuilder(unitId, lessonId, pathVersionId, pathRevision);
			if (!result.builder_id) throw new Error('Builder lesson is not ready yet. Please try again.');
			await goto(`/builder/${encodeURIComponent(result.builder_id)}`);
		} catch (err) {
			opened = false;
			error = err instanceof Error ? err.message : 'Could not open the lesson in Builder.';
		} finally {
			busy = null;
		}
	}

	function applyProgress(next: LessonGenerationProgress): void {
		progress = next;
		if (stage(next.stage) === 'complete') {
			stopPolling();
			if (generationInitiated) void openBuilder();
		} else if (stage(next.stage) === 'running' || stage(next.stage) === 'partial') {
			startPolling();
		} else {
			stopPolling();
		}
	}

	async function poll(): Promise<void> {
		if (pollInFlight || busy === 'opening') return;
		pollInFlight = true;
		try { applyProgress(await getLessonGenerationProgress(unitId, lessonId)); }
		catch (err) { error = err instanceof Error ? err.message : 'Could not load lesson generation progress.'; }
		finally { pollInFlight = false; }
	}

	async function loadReview(): Promise<void> {
		busy = 'loading';
		error = null;
		try {
			review = await reviewLessonGeneration(unitId, lessonId, pathVersionId, pathRevision);
			if (stage(initialStage) === 'complete' && stage(review.stage) !== 'failed') {
				review = { ...review, stage: 'complete', builder_id: review.builder_id ?? initialBuilderId };
			}
			if (stage(review.stage) === 'running' || stage(review.stage) === 'partial') startPolling();
			if (stage(review.stage) === 'complete') progress = review;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Could not load the lesson review.';
		} finally { busy = null; }
	}

	async function approve(): Promise<void> {
		busy = 'approving'; error = null;
		try {
			const next = await approveLessonGeneration(unitId, lessonId, pathVersionId, pathRevision);
			generationInitiated = true;
			applyProgress(next);
		}
		catch (err) { error = err instanceof Error ? err.message : 'Could not approve the lesson generation.'; }
		finally { busy = null; }
	}

	async function retry(): Promise<void> {
		busy = 'retrying'; error = null;
		try {
			const next = await retryLessonGeneration(unitId, lessonId, pathVersionId, pathRevision);
			generationInitiated = true;
			applyProgress(next);
		}
		catch (err) { error = err instanceof Error ? err.message : 'Could not retry the lesson generation.'; }
		finally { busy = null; }
	}

	onMount(() => { void loadReview(); });
	onDestroy(stopPolling);
</script>

<div class="generation-review" aria-live="polite">
	<p class="eyebrow">Lesson writing</p>
	<h4>{currentStage === 'awaiting_review' ? 'Ready for your review' : currentStage === 'running' ? 'Writing the lesson…' : currentStage === 'partial' ? 'Lesson partly written' : currentStage === 'failed' ? 'Lesson writing needs attention' : 'Lesson ready'}</h4>
	{#if review?.display_title}<h5>{review.display_title}</h5>{/if}
	{#if review?.review_cards?.length}
		<div class="review-cards">
			{#each review.review_cards as card}
				<article class="review-card">
					<strong>{card.title}</strong>
					<p>{card.objective}</p>
					{#if card.prereqs.length}<small>Prerequisites: {card.prereqs.join(', ')}</small>{/if}
					{#if card.misconception_descriptions.length}<small>Watch for: {card.misconception_descriptions.join('; ')}</small>{/if}
				</article>
			{/each}
		</div>
	{/if}
	{#if error}<p class="error">{error}</p>{/if}
	{#if currentStage === 'awaiting_review'}
		<p>Review the planned lesson, then approve writing it.</p>
		<button class="primary" type="button" disabled={busy !== null} onclick={approve}>{busy === 'approving' ? 'Starting…' : 'Approve and write lesson'}</button>
	{:else if currentStage === 'running' || currentStage === 'partial'}
		<p>You can stay here while the lesson is written.</p>
	{:else if currentStage === 'failed' && retryable}
		<p>The lesson was not completed. Your path is still safe.</p>
		<button class="primary" type="button" disabled={busy !== null} onclick={retry}>{busy === 'retrying' ? 'Retrying…' : 'Retry writing'}</button>
	{:else if currentStage === 'failed'}
		<p>The lesson was not completed. This generation cannot be retried from here.</p>
	{:else if currentStage === 'complete' && !opened}
		<button class="primary" type="button" disabled={busy !== null} onclick={openBuilder}>{busy === 'opening' ? 'Opening Builder…' : 'Open in Builder'}</button>
	{/if}
</div>

<script lang="ts">
	import { onDestroy } from 'svelte';

	import V3InputSurface from '$lib/components/studio/V3InputSurface.svelte';
	import V3PlanningState from '$lib/components/studio/V3PlanningState.svelte';
	import V3SignalConfirmation from '$lib/components/studio/V3SignalConfirmation.svelte';
	import V3Clarification from '$lib/components/studio/V3Clarification.svelte';
	import V3BlueprintPreview from '$lib/components/studio/V3BlueprintPreview.svelte';
	import V3Canvas from '$lib/components/studio/V3Canvas.svelte';

	import {
		adjustBlueprint,
		connectV3StudioGenerationStream,
		downloadV3GenerationPdf,
		extractSignals,
		generateBlueprint,
		getClarifications,
		startV3Generation
	} from '$lib/api/v3';
	import { isApiError } from '$lib/api/errors';
	import { resetV3Studio, v3Studio } from '$lib/stores/v3-studio.svelte';
	import {
		buildCanvasSkeleton,
		mergeComponentField,
		mergeDiagramFrame,
		mergePracticeProblem
	} from '$lib/studio/v3-canvas';
	import { hasRequiredStructuredFields } from '$lib/studio/v3-clarify';
	import type { V3ClarificationAnswer, V3InputForm } from '$lib/types/v3';

	let pdfLoading = $state(false);
	let pdfError = $state<string | null>(null);

	function friendly(err: unknown): string {
		if (isApiError(err)) return err.detail;
		if (err instanceof Error) return err.message;
		return 'Something went wrong. Try again.';
	}

	async function handleInputSubmit(form: V3InputForm) {
		v3Studio.error = null;
		v3Studio.form = form;
		v3Studio.stage = 'planning';
		try {
			v3Studio.signals = await extractSignals(form);
			v3Studio.stage = 'confirming';
		} catch (err) {
			v3Studio.stage = 'input';
			v3Studio.error = friendly(err);
		}
	}

	async function handleSignalsConfirmed() {
		v3Studio.error = null;
		const signals = v3Studio.signals;
		const form = v3Studio.form;
		if (!signals || !form) return;

		if (hasRequiredStructuredFields(form)) {
			await runLessonArchitect();
			return;
		}

		if (signals.missing_signals.length > 0) {
			v3Studio.stage = 'planning';
			try {
				v3Studio.clarifications = await getClarifications(signals, form);
				if (v3Studio.clarifications.length === 0) {
					await runLessonArchitect();
				} else {
					v3Studio.stage = 'clarifying';
				}
			} catch (err) {
				v3Studio.stage = 'confirming';
				v3Studio.error = friendly(err);
			}
		} else {
			await runLessonArchitect();
		}
	}

	function handleSignalCorrection() {
		v3Studio.error = null;
		v3Studio.stage = 'input';
	}

	async function handleClarificationAnswered(answers: V3ClarificationAnswer[]) {
		v3Studio.answers = answers;
		await runLessonArchitect();
	}

	async function runLessonArchitect() {
		v3Studio.error = null;
		v3Studio.stage = 'planning';
		const signals = v3Studio.signals;
		const form = v3Studio.form;
		if (!signals || !form) return;
		try {
			const blueprint = await generateBlueprint({
				signals,
				form,
				clarification_answers: v3Studio.answers
			});
			v3Studio.blueprint = blueprint;
			v3Studio.stage = 'reviewing';
		} catch (err) {
			v3Studio.stage = v3Studio.clarifications.length ? 'clarifying' : 'confirming';
			v3Studio.error = friendly(err);
		}
	}

	async function handleBlueprintApproved() {
		v3Studio.error = null;
		const blueprint = v3Studio.blueprint;
		if (!blueprint) return;

		const generationId = crypto.randomUUID();
		v3Studio.generationId = generationId;
		v3Studio.canvas = buildCanvasSkeleton(blueprint);
		v3Studio.stage = 'generating';

		try {
			await startV3Generation({
				generation_id: generationId,
				blueprint_id: blueprint.blueprint_id,
				template_id: blueprint.template_id
			});
		} catch (err) {
			v3Studio.stage = 'reviewing';
			v3Studio.error = friendly(err);
			return;
		}

		v3Studio.streamCancel?.();
		v3Studio.streamCancel = connectV3StudioGenerationStream(generationId, {
			onCoherenceReviewStarted: () => {
				v3Studio.stage = 'finalising';
			},
			onCoherenceReportReady: (data) => {
				const blocking = typeof data.blocking_count === 'number' ? data.blocking_count : 0;
				const repairs =
					typeof data.repair_target_count === 'number' ? data.repair_target_count : 0;
				v3Studio.coherenceHint =
					repairs > 0
						? `Consistency pass: ${blocking} blocking issues flagged — refining (${repairs} repair targets).`
						: 'Consistency review finished.';
			},
			onResourceFinalised: () => {
				v3Studio.streamCancel?.();
				v3Studio.streamCancel = null;
				v3Studio.stage = 'complete';
			},
			onComponentReady: (data) => {
				const sid = String(data.section_id ?? '');
				const cid = String(data.component_id ?? '');
				const field = String(data.section_field ?? '');
				const raw = data.data;
				const pdata =
					typeof raw === 'object' && raw !== null ? (raw as Record<string, unknown>) : {};
				if (!sid || !cid || !field) return;
				v3Studio.canvas = v3Studio.canvas.map((s) =>
					s.id !== sid
						? s
						: {
								...s,
								mergedFields: mergeComponentField(s.mergedFields, field, pdata),
								components: s.components.map((c) =>
									c.id === cid ? { ...c, status: 'ready' as const, data: pdata } : c
								)
							}
				);
			},
			onVisualReady: (data) => {
				const sid = String(data.attaches_to ?? '');
				const url = typeof data.image_url === 'string' ? data.image_url : null;
				const fi =
					data.frame_index === undefined ? null : (data.frame_index as number | null);
				if (!sid) return;
				v3Studio.canvas = v3Studio.canvas.map((s) => {
					if (s.id !== sid) return s;
					const mergedFields = mergeDiagramFrame(s.mergedFields, {
						image_url: url,
						frame_index: fi
					});
					const visual = s.visual
						? {
								...s.visual,
								status: 'ready' as const,
								image_url: url ?? s.visual.image_url,
								frame_index: fi ?? s.visual.frame_index
							}
						: null;
					return { ...s, mergedFields, visual };
				});
			},
			onQuestionReady: (data) => {
				const sid = String(data.section_id ?? '');
				const qid = String(data.question_id ?? '');
				const diff = String(data.difficulty ?? 'warm');
				const raw = data.data;
				const pdata =
					typeof raw === 'object' && raw !== null ? (raw as Record<string, unknown>) : {};
				if (!sid || !qid) return;
				v3Studio.canvas = v3Studio.canvas.map((s) =>
					s.id !== sid
						? s
						: {
								...s,
								mergedFields: mergePracticeProblem(s.mergedFields, qid, diff, pdata),
								questions: s.questions.map((q) =>
									q.id === qid ? { ...q, status: 'ready' as const, data: pdata } : q
								)
							}
				);
			},
			onComponentPatched: (data) => {
				const sid = String(data.section_id ?? '');
				const cid = String(data.component_id ?? '');
				const field = String(data.section_field ?? '');
				const raw = data.data;
				const pdata =
					typeof raw === 'object' && raw !== null ? (raw as Record<string, unknown>) : {};
				if (!sid || !cid || !field) return;
				v3Studio.canvas = v3Studio.canvas.map((s) =>
					s.id !== sid
						? s
						: {
								...s,
								mergedFields: mergeComponentField(s.mergedFields, field, pdata),
								components: s.components.map((c) =>
									c.id === cid ? { ...c, status: 'patched' as const, data: pdata } : c
								)
							}
				);
			},
			onGenerationWarning: (data) => {
				v3Studio.error = friendly(data.message ?? 'Generation warning');
			},
			onError: (err) => {
				v3Studio.error = friendly(err);
			}
		});
	}

	async function handleBlueprintAdjust(instruction: string) {
		v3Studio.error = null;
		const blueprint = v3Studio.blueprint;
		if (!blueprint) return;
		v3Studio.stage = 'planning';
		try {
			v3Studio.blueprint = await adjustBlueprint({
				blueprint_id: blueprint.blueprint_id,
				adjustment: instruction
			});
			v3Studio.stage = 'reviewing';
		} catch (err) {
			v3Studio.stage = 'reviewing';
			v3Studio.error = friendly(err);
		}
	}

	onDestroy(() => {
		v3Studio.streamCancel?.();
	});

	async function handleDownloadPdf() {
		const gid = v3Studio.generationId;
		if (!gid) {
			pdfError = 'No generation id — try generating again.';
			return;
		}
		pdfLoading = true;
		pdfError = null;
		try {
			const canvasPayload = JSON.parse(JSON.stringify(v3Studio.canvas)) as Record<string, unknown>[];
			await downloadV3GenerationPdf(gid, {
				school_name: '—',
				teacher_name: '—',
				include_toc: false,
				include_answers: true,
				canvas_sections: canvasPayload
			});
		} catch (err) {
			pdfError = friendly(err);
		} finally {
			pdfLoading = false;
		}
	}
</script>

<div class="min-h-screen bg-background pb-16">
	<div class="sticky top-0 z-10 border-b border-border/60 bg-background/95 px-4 py-3 backdrop-blur supports-[backdrop-filter]:bg-background/75">
		<div class="mx-auto flex max-w-5xl items-center justify-between gap-3">
			<span class="text-sm font-semibold tracking-tight">Studio</span>
			<button
				type="button"
				class="text-xs text-muted-foreground underline-offset-4 hover:underline"
				onclick={() => resetV3Studio()}
			>
				Start over
			</button>
		</div>
	</div>

	{#if v3Studio.stage === 'input'}
		<V3InputSurface onSubmit={handleInputSubmit} />
	{:else if v3Studio.stage === 'confirming' && v3Studio.signals}
		<V3SignalConfirmation signals={v3Studio.signals} onConfirm={handleSignalsConfirmed} onCorrect={handleSignalCorrection} />
	{:else if v3Studio.stage === 'clarifying' && v3Studio.clarifications.length}
		<V3Clarification questions={v3Studio.clarifications} onAnswered={handleClarificationAnswered} />
	{:else if v3Studio.stage === 'planning'}
		<V3PlanningState form={v3Studio.form} />
	{:else if v3Studio.stage === 'reviewing' && v3Studio.blueprint}
		<V3BlueprintPreview blueprint={v3Studio.blueprint} onApprove={handleBlueprintApproved} onAdjust={handleBlueprintAdjust} />
	{:else if v3Studio.stage === 'generating' || v3Studio.stage === 'finalising'}
		{#if v3Studio.coherenceHint && v3Studio.stage === 'finalising'}
			<p class="mx-auto max-w-3xl px-4 pt-6 text-center text-sm text-muted-foreground">{v3Studio.coherenceHint}</p>
		{/if}
		<V3Canvas sections={v3Studio.canvas} stage={v3Studio.stage} templateId={v3Studio.blueprint?.template_id ?? 'guided-concept-path'} />
	{:else if v3Studio.stage === 'complete'}
		<div class="mx-auto flex max-w-3xl justify-end gap-3 px-4 pt-4">
			<button
				type="button"
				class="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60"
				onclick={handleDownloadPdf}
				disabled={pdfLoading}
			>
				{pdfLoading ? 'Generating PDF…' : 'Download PDF'}
			</button>
		</div>
		{#if pdfError}
			<p class="mx-auto max-w-3xl px-4 pt-2 text-center text-sm text-destructive" role="alert">{pdfError}</p>
		{/if}
		<V3Canvas sections={v3Studio.canvas} stage="complete" templateId={v3Studio.blueprint?.template_id ?? 'guided-concept-path'} />
	{/if}

	{#if v3Studio.error}
		<p class="mx-auto mt-6 max-w-xl px-4 text-center text-sm text-destructive" role="alert">{v3Studio.error}</p>
	{/if}
</div>

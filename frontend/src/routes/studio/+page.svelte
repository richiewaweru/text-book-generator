<script lang="ts">
	import { onDestroy } from 'svelte';

	import V3InputSurface from '$lib/components/studio/V3InputSurface.svelte';
	import V3PlanningState from '$lib/components/studio/V3PlanningState.svelte';
	import V3SignalConfirmation from '$lib/components/studio/V3SignalConfirmation.svelte';
	import V3Clarification from '$lib/components/studio/V3Clarification.svelte';
	import V3BlueprintPreview from '$lib/components/studio/V3BlueprintPreview.svelte';
	import V3Canvas from '$lib/components/studio/V3Canvas.svelte';
	import V3BookletPackView from '$lib/components/studio/V3BookletPackView.svelte';
	import V3SupplementTray from '$lib/components/studio/V3SupplementTray.svelte';

	import {
		adjustBlueprint,
		connectV3StudioGenerationStream,
		createV3SupplementBlueprint,
		downloadV3GenerationPdf,
		extractSignals,
		fetchV3Document,
		generateBlueprint,
		getClarifications,
		getV3SupplementOptions,
		startV3Generation
	} from '$lib/api/v3';
	import { isApiError } from '$lib/api/errors';
	import {
		captureParentSnapshot,
		resetV3Studio,
		restoreParentFromSupplementReview,
		v3Studio
	} from '$lib/stores/v3-studio.svelte';
	import {
		applyComponentPatchedToCanvas,
		applyComponentReadyToCanvas,
		applySectionWriterFailedToCanvas
	} from '$lib/studio/v3-stream-state';
	import {
		buildCanvasSkeleton,
		mergeDiagramFrame,
		mergePracticeProblem
	} from '$lib/studio/v3-canvas';
	import { mapPackSectionsToCanvas } from '$lib/studio/v3-print-canvas';
	import { getBookletExportPolicy, isBookletStatus } from '$lib/studio/v3-booklet';
	import { coerceV3DocumentToPack } from '$lib/studio/v3-document';
	import type {
		BookletStatus,
		V3ClarificationAnswer,
		V3DraftPack,
		V3InputForm,
		V3SupplementResourceType
	} from '$lib/types/v3';

	let pdfLoading = $state(false);
	let pdfError = $state<string | null>(null);
	let pdfConfirming = $state(false);
	let pdfOpen = $state(false);
	let pendingSupplementLabel = $state<string | null>(null);
	let schoolName = $state('');
	let teacherName = $state('');
	let exportDate = $state('');
	let includeAnswers = $state(true);
	const currentExportPolicy = $derived(getBookletExportPolicy(v3Studio.bookletStatus));

	function friendly(err: unknown): string {
		if (isApiError(err)) return err.detail;
		if (err instanceof Error) return err.message;
		return 'Something went wrong. Try again.';
	}

	function parsePack(payload: unknown): V3DraftPack | null {
		if (typeof payload !== 'object' || payload === null) return null;
		const candidate = (payload as { pack?: unknown }).pack;
		if (typeof candidate !== 'object' || candidate === null) return null;
		return candidate as V3DraftPack;
	}

	function statusFromPayload(payload: Record<string, unknown>, fallback: BookletStatus): BookletStatus {
		return isBookletStatus(payload.booklet_status) ? payload.booklet_status : fallback;
	}

	async function hydrateFromDocument(generationId: string): Promise<boolean> {
		try {
			const document = await fetchV3Document(generationId);
			const pack = coerceV3DocumentToPack(generationId, document, {
				templateId: v3Studio.blueprint?.template_id ?? 'guided-concept-path'
			});
			if (!pack) return false;
			v3Studio.draftPack = pack;
			v3Studio.activePack = pack;
			if (pack.status === 'final_ready' || pack.status === 'final_with_warnings') {
				v3Studio.finalPack = pack;
			}
			v3Studio.bookletStatus = pack.status;
			v3Studio.bookletIssues = pack.booklet_issues;
			v3Studio.canvas = mapPackSectionsToCanvas(pack.sections);
			if (pack.status !== 'streaming_preview') {
				v3Studio.coherenceHint = null;
				v3Studio.stage = 'complete';
				if (!v3Studio.supplementContext) {
					void loadSupplementOptions(generationId);
				}
			}
			return true;
		} catch {
			return false;
		}
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

		v3Studio.stage = 'planning';
		try {
			v3Studio.clarifications = await getClarifications(signals, form);
			if (v3Studio.clarifications.length === 0) {
				await runLessonArchitect();
			} else {
				v3Studio.stage = 'clarifying';
			}
		} catch (err) {
			console.warn('Clarify failed, proceeding to blueprint:', err);
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

	async function loadSupplementOptions(generationId: string | null): Promise<void> {
		if (!generationId) return;
		v3Studio.supplementOptionsLoading = true;
		v3Studio.supplementOptionsError = null;
		try {
			const res = await getV3SupplementOptions(generationId);
			v3Studio.supplementOptions = res.available ? res.options : [];
			v3Studio.supplementOptionsError = res.unavailable_reason;
		} catch (err) {
			v3Studio.supplementOptions = [];
			v3Studio.supplementOptionsError = friendly(err);
		} finally {
			v3Studio.supplementOptionsLoading = false;
		}
	}

	async function handleCreateSupplementPlan(resourceType: V3SupplementResourceType) {
		const parentGenerationId = v3Studio.generationId;
		if (!parentGenerationId) return;

		v3Studio.error = null;
		v3Studio.parentSnapshot = captureParentSnapshot();
		pendingSupplementLabel =
			v3Studio.supplementOptions.find((option) => option.resource_type === resourceType)?.label ??
			'companion resource';
		v3Studio.stage = 'planning';

		try {
			const result = await createV3SupplementBlueprint({
				parent_generation_id: parentGenerationId,
				resource_type: resourceType
			});

			v3Studio.blueprint = result.preview;
			v3Studio.supplementContext = {
				mode: 'supplement_review',
				parentGenerationId: result.parent_generation_id,
				parentTitle: result.parent_title,
				resourceType: result.resource_type,
				label: result.label,
				childGenerationId: result.generation_id,
				childBlueprintId: result.blueprint_id
			};
			v3Studio.stage = 'reviewing';
			pendingSupplementLabel = null;
		} catch (err) {
			restoreParentFromSupplementReview();
			pendingSupplementLabel = null;
			v3Studio.error = friendly(err);
		}
	}

	async function handleBlueprintApproved() {
		v3Studio.error = null;
		const blueprint = v3Studio.blueprint;
		if (!blueprint) return;

		const generationId = v3Studio.supplementContext?.childGenerationId ?? crypto.randomUUID();
		v3Studio.generationId = generationId;
		v3Studio.canvas = buildCanvasSkeleton(blueprint);
		v3Studio.draftPack = null;
		v3Studio.finalPack = null;
		v3Studio.activePack = null;
		v3Studio.bookletStatus = 'streaming_preview';
		v3Studio.bookletIssues = [];
		v3Studio.stage = 'generating';
		v3Studio.progressLabel = null;

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

		if (v3Studio.supplementContext) {
			v3Studio.supplementContext = {
				...v3Studio.supplementContext,
				mode: 'supplement_generation'
			};
			v3Studio.parentSnapshot = null;
			v3Studio.supplementOptions = [];
			v3Studio.supplementOptionsError = null;
		}

		v3Studio.streamCancel?.();
		v3Studio.streamCancel = connectV3StudioGenerationStream(generationId, {
			onProgressUpdate: (data) => {
				const label = typeof data.label === 'string' ? data.label.trim() : '';
				if (label) {
					v3Studio.progressLabel = label;
				}
			},
			onCoherenceReviewStarted: () => {
				v3Studio.stage = 'finalising';
			},
			onCoherenceReportReady: (data) => {
				const blocking = typeof data.blocking_count === 'number' ? data.blocking_count : 0;
				const repairs =
					typeof data.repair_target_count === 'number' ? data.repair_target_count : 0;
				v3Studio.coherenceHint =
					repairs > 0
						? `Consistency pass: ${blocking} blocking issues flagged - refining (${repairs} repair targets).`
						: 'Consistency review finished.';
			},
			onDraftPackReady: (data) => {
				const pack = parsePack(data);
				if (!pack) return;
				const status = statusFromPayload(data, pack.status);
				v3Studio.draftPack = pack;
				v3Studio.activePack = pack;
				v3Studio.bookletStatus = status;
				v3Studio.bookletIssues = Array.isArray(pack.booklet_issues) ? pack.booklet_issues : [];
			},
			onFinalPackReady: (data) => {
				const pack = parsePack(data);
				if (!pack) return;
				const status = statusFromPayload(data, pack.status);
				v3Studio.finalPack = pack;
				v3Studio.activePack = pack;
				v3Studio.bookletStatus = status;
				v3Studio.bookletIssues = Array.isArray(pack.booklet_issues) ? pack.booklet_issues : [];
			},
			onDraftStatusUpdated: (data) => {
				const status = statusFromPayload(data, v3Studio.bookletStatus);
				const pack = parsePack(data);
				if (pack) {
					v3Studio.draftPack = pack;
					v3Studio.activePack = pack;
					v3Studio.bookletIssues = Array.isArray(pack.booklet_issues) ? pack.booklet_issues : [];
				}
				v3Studio.bookletStatus = status;
			},
			onResourceFinalised: () => {
				const gid = v3Studio.generationId;
				if (gid) {
					void hydrateFromDocument(gid);
				}
				v3Studio.streamCancel?.();
				v3Studio.streamCancel = null;
				v3Studio.stage = 'complete';
				if (v3Studio.supplementContext?.mode === 'supplement_generation') {
					v3Studio.supplementContext = null;
				}
			},
			onComponentReady: (data) => {
				const next = applyComponentReadyToCanvas(v3Studio.canvas, data);
				v3Studio.canvas = next.canvas;
				if (next.warning) {
					console.warn('component_ready warning', data);
					v3Studio.error = next.warning;
				}
			},
			onSectionWriterFailed: (data) => {
				const next = applySectionWriterFailedToCanvas(v3Studio.canvas, data);
				v3Studio.canvas = next.canvas;
				if (next.warning) {
					v3Studio.error = next.warning;
				}
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
				const next = applyComponentPatchedToCanvas(v3Studio.canvas, data);
				v3Studio.canvas = next.canvas;
				if (next.warning) {
					console.warn('component_patched warning', data);
					v3Studio.error = next.warning;
				}
			},
			onGenerationWarning: (data) => {
				v3Studio.error = friendly(data.message ?? 'Generation warning');
			},
			onGenerationComplete: () => {
				const gid = v3Studio.generationId;
				if (gid) {
					void hydrateFromDocument(gid);
				}
			},
			onOpen: () => {
				const gid = v3Studio.generationId;
				if (gid && !v3Studio.activePack) {
					void hydrateFromDocument(gid);
				}
			},
			onError: (err) => {
				v3Studio.error = friendly(err);
				const gid = v3Studio.generationId;
				if (gid && !v3Studio.activePack) {
					void hydrateFromDocument(gid);
				}
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
			pdfError = 'No generation id - try generating again.';
			return;
		}
		const policy = currentExportPolicy;
		if (!policy.enabled) {
			pdfError = 'Export is unavailable for the current booklet status.';
			return;
		}
		if (policy.requiresConfirm && !pdfConfirming) {
			pdfConfirming = true;
			const proceed = window.confirm(
				'This draft needs review before classroom use. Export this draft anyway?'
			);
			pdfConfirming = false;
			if (!proceed) return;
		}
		if (!schoolName.trim() || !teacherName.trim()) {
			pdfError = 'School name and teacher name are required.';
			return;
		}
		pdfLoading = true;
		pdfError = null;
		try {
			await downloadV3GenerationPdf(gid, {
				school_name: schoolName.trim(),
				teacher_name: teacherName.trim(),
				date: exportDate.trim() || null,
				include_toc: false,
				include_answers: includeAnswers
			});
			pdfOpen = false;
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
		<V3PlanningState
			form={v3Studio.form}
			planningLabel={pendingSupplementLabel
				? `Creating your ${pendingSupplementLabel} plan`
				: undefined}
			messages={pendingSupplementLabel
				? [
						'Reading the parent lesson blueprint…',
						'Loading the resource rules…',
						'Creating a focused companion plan…',
						'Checking the plan against the resource spec…'
					]
				: undefined}
		/>
	{:else if v3Studio.stage === 'reviewing' && v3Studio.blueprint}
		<V3BlueprintPreview
			blueprint={v3Studio.blueprint}
			contextLabel={v3Studio.supplementContext
				? `${v3Studio.supplementContext.label} plan`
				: 'Lesson plan'}
			approveLabel={v3Studio.supplementContext
				? `Approve and generate ${v3Studio.supplementContext.label}`
				: 'Approve and generate'}
			cancelLabel="Back to lesson"
			parentTitle={v3Studio.supplementContext?.parentTitle ?? null}
			onCancel={v3Studio.supplementContext ? restoreParentFromSupplementReview : undefined}
			onApprove={handleBlueprintApproved}
			onAdjust={handleBlueprintAdjust}
		/>
	{:else if v3Studio.stage === 'generating' || v3Studio.stage === 'finalising' || v3Studio.stage === 'complete'}
		{#if v3Studio.stage === 'complete'}
			<div class="mx-auto max-w-4xl px-4 pt-6 pb-2">
				<div
					class="flex items-center justify-between gap-4 rounded-xl border border-border/60 bg-card p-4 shadow-sm"
				>
					<div>
						<p class="text-sm font-semibold">Your booklet is ready</p>
						<p class="mt-0.5 text-xs text-muted-foreground">
							Review it below or download a printable PDF.
						</p>
					</div>
					<span class="rounded-full bg-green-50 px-3 py-1 text-xs font-medium text-green-700">
						Ready ✓
					</span>
				</div>
			</div>
		{/if}
		{#if v3Studio.activePack}
			<div class="mx-auto max-w-4xl px-4 pt-4">
				<div class="flex justify-end">
					<button
						type="button"
						class="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60"
						onclick={() => (pdfOpen = !pdfOpen)}
						disabled={!currentExportPolicy.enabled}
					>
						{currentExportPolicy.label}
					</button>
				</div>
				{#if pdfOpen}
					<div class="mt-3 rounded-lg border border-border/60 bg-card p-4 space-y-3">
						<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
							<label class="flex flex-col gap-1 text-sm">
								School name
								<input
									bind:value={schoolName}
									placeholder="Springfield High"
									class="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
								/>
							</label>
							<label class="flex flex-col gap-1 text-sm">
								Teacher name
								<input
									bind:value={teacherName}
									placeholder="Ms. Johnson"
									class="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
								/>
							</label>
							<label class="flex flex-col gap-1 text-sm">
								Date (optional)
								<input
									bind:value={exportDate}
									type="date"
									class="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
								/>
							</label>
						</div>
						<label class="flex items-center gap-2 text-sm">
							<input bind:checked={includeAnswers} type="checkbox" />
							Include answers
						</label>
						{#if pdfError}
							<p class="text-sm text-destructive" role="alert">{pdfError}</p>
						{/if}
						<button
							type="button"
							class="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60"
							onclick={handleDownloadPdf}
							disabled={pdfLoading || !schoolName.trim() || !teacherName.trim()}
						>
							{pdfLoading ? 'Generating PDF...' : 'Download PDF'}
						</button>
					</div>
				{/if}
			</div>
		{/if}
		{#if v3Studio.coherenceHint && v3Studio.stage === 'finalising'}
			<p class="mx-auto max-w-3xl px-4 pt-6 text-center text-sm text-muted-foreground">{v3Studio.coherenceHint}</p>
		{/if}
		{#if v3Studio.stage === 'complete' && v3Studio.generationId}
			<V3SupplementTray
				parentGenerationId={v3Studio.generationId}
				options={v3Studio.supplementOptions}
				loading={v3Studio.supplementOptionsLoading}
				error={v3Studio.supplementOptionsError}
				unavailableReason={v3Studio.supplementOptionsError}
				onCreatePlan={handleCreateSupplementPlan}
			/>
		{/if}
		{#if v3Studio.activePack}
			<V3BookletPackView
				pack={v3Studio.activePack}
				status={v3Studio.bookletStatus}
				issues={v3Studio.bookletIssues}
			/>
			<details class="mx-auto max-w-4xl px-4 pb-6">
				<summary class="cursor-pointer text-sm font-medium text-muted-foreground">Show generation progress</summary>
				<div class="pt-4">
					<V3Canvas
						sections={v3Studio.canvas}
						stage={v3Studio.stage}
						templateId={v3Studio.blueprint?.template_id ?? 'guided-concept-path'}
						statusLabel={v3Studio.progressLabel}
					/>
				</div>
			</details>
		{:else}
			<V3Canvas
				sections={v3Studio.canvas}
				stage={v3Studio.stage}
				templateId={v3Studio.blueprint?.template_id ?? 'guided-concept-path'}
				statusLabel={v3Studio.progressLabel}
			/>
		{/if}
	{/if}

	{#if v3Studio.error}
		<p class="mx-auto mt-6 max-w-xl px-4 text-center text-sm text-destructive" role="alert">{v3Studio.error}</p>
	{/if}
</div>

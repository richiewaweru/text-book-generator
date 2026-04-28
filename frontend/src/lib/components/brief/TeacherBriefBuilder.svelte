<script lang="ts">
	import { onMount } from 'svelte';

	import {
		commitPlan,
		planFromBrief,
		resolveTopic,
		reviewTeacherBrief,
		validateTeacherBrief
	} from '$lib/api/teacher-brief';
	import { getProfile } from '$lib/api/profile';
	import {
		briefSteps,
		buildLearnerContext,
		learnerContextChips,
		recommendSupports,
		stepSummary
	} from '$lib/brief/config';
	import GenerationView from '$lib/components/studio/GenerationView.svelte';
	import { resetGenerationState, setGenerationAccepted } from '$lib/stores/studio';
	import type {
		BriefBuilderStep,
		BriefReviewWarning,
		BriefValidationResult,
		BuilderWarning,
		GenerationAccepted,
		PlanningGenerationSpec,
		TeacherBrief,
		TeacherBriefSupport,
		TopicResolutionSubtopic
	} from '$lib/types';

	import BriefReviewCard from './BriefReviewCard.svelte';
	import BriefStepCard from './BriefStepCard.svelte';
	import DepthStep from './DepthStep.svelte';
	import LearnerContextStep from './LearnerContextStep.svelte';
	import OutcomeStep from './OutcomeStep.svelte';
	import PlanReviewStep from './PlanReviewStep.svelte';
	import ResourceTypeStep from './ResourceTypeStep.svelte';
	import SubtopicChoiceStep from './SubtopicChoiceStep.svelte';
	import SupportsStep from './SupportsStep.svelte';
	import TopicInputStep from './TopicInputStep.svelte';

	type BuilderStage = 'building' | 'planning' | 'reviewing' | 'generating';

	let stage = $state<BuilderStage>('building');
	let active_step = $state<BriefBuilderStep>('topic');
	let completed_steps = $state<BriefBuilderStep[]>([]);
	let brief = $state<Partial<TeacherBrief>>({
		subtopics: [],
		supports: [],
		depth: 'standard',
		teacher_notes: ''
	});
	let suggestions = $state<{ subtopics?: TopicResolutionSubtopic[] }>({});
	let warnings = $state<BuilderWarning[]>([]);
	let loading = $state(false);
	let validationResult = $state<BriefValidationResult | null>(null);
	let reviewWarnings = $state<BriefReviewWarning[]>([]);
	let rawTopic = $state('');
	let customSubtopic = $state('');
	let learnerText = $state('');
	let selectedLearnerChips = $state<string[]>([]);
	let recommendedSupports = $state<TeacherBriefSupport[]>([]);
	let topicStatusMessage = $state<string | null>(null);
	let apiError = $state<string | null>(null);
	let plannedSpec = $state<PlanningGenerationSpec | null>(null);
	let acceptedGeneration = $state<GenerationAccepted | null>(null);

	const learnerSummary = $derived(learnerText || selectedLearnerChips.join(', '));
	const reviewReady = $derived(
		Boolean(
			brief.subject &&
				brief.topic &&
				brief.subtopics?.length &&
				brief.learner_context &&
				brief.intended_outcome &&
				brief.resource_type &&
				brief.depth
		)
	);
	const briefIsReady = $derived(Boolean(validationResult?.is_ready));

	function resetPlanStage() {
		stage = 'building';
		plannedSpec = null;
		acceptedGeneration = null;
		resetGenerationState();
	}

	function clearValidation() {
		validationResult = null;
		warnings = [];
		reviewWarnings = [];
		apiError = null;
	}

	function markStepCompleted(step: BriefBuilderStep) {
		if (!completed_steps.includes(step)) {
			completed_steps = [...completed_steps, step];
		}
	}

	function moveToStep(current: BriefBuilderStep, next: BriefBuilderStep) {
		markStepCompleted(current);
		active_step = next;
	}

	function editStep(step: BriefBuilderStep) {
		active_step = step;
		clearValidation();
		if (stage !== 'building') {
			resetPlanStage();
		}
	}

	function isVisible(step: BriefBuilderStep): boolean {
		return (
			completed_steps.includes(step) ||
			step === active_step ||
			briefSteps.indexOf(step) <= briefSteps.indexOf(active_step)
		);
	}

	function syncLearnerContext(nextText: string, chips = selectedLearnerChips) {
		learnerText = nextText;
		brief = {
			...brief,
			learner_context: buildLearnerContext(nextText, chips)
		};
	}

	function updateSupportRecommendations() {
		recommendedSupports = recommendSupports({
			resourceType: brief.resource_type,
			intendedOutcome: brief.intended_outcome,
			learnerContext: learnerText,
			learnerChips: selectedLearnerChips
		});
		brief = {
			...brief,
			supports: recommendedSupports
		};
	}

	function resetSupportSelections() {
		recommendedSupports = [];
		brief = {
			...brief,
			supports: []
		};
		clearValidation();
	}

	function resetAfterTopicChange() {
		brief = {
			...brief,
			subject: '',
			topic: '',
			subtopics: [],
			supports: []
		};
		suggestions = {};
		customSubtopic = '';
		recommendedSupports = [];
		completed_steps = completed_steps.filter(
			(step) => !['choose_subtopic', 'supports', 'review'].includes(step)
		);
		clearValidation();
		resetPlanStage();
	}

	function nextStepAfterSubtopic(): BriefBuilderStep {
		if (!brief.learner_context) return 'learner_context';
		if (!brief.intended_outcome) return 'intended_outcome';
		if (!brief.resource_type) return 'resource_type';
		return 'supports';
	}

	function handleTopicInput(value: string) {
		rawTopic = value;
		if (brief.topic && value.trim() && value.trim() !== brief.topic) {
			resetAfterTopicChange();
		}
	}

	async function handleTopicSubmit() {
		if (!rawTopic.trim()) return;
		loading = true;
		apiError = null;
		topicStatusMessage = 'Finding the main ideas teachers usually teach under this topic...';
		clearValidation();
		try {
			const result = await resolveTopic({
				raw_topic: rawTopic.trim(),
				learner_context: brief.learner_context || undefined
			});
			brief = {
				...brief,
				subject: result.subject,
				topic: result.topic,
				subtopics: [],
				supports: []
			};
			suggestions = { subtopics: result.candidate_subtopics };
			customSubtopic = '';
			recommendedSupports = [];
			topicStatusMessage = result.clarification_message ?? null;
			moveToStep('topic', 'choose_subtopic');
		} catch (error) {
			apiError = error instanceof Error ? error.message : 'Topic resolution failed.';
			topicStatusMessage = null;
		} finally {
			loading = false;
		}
	}

	function handleSubtopicToggle(value: string) {
		const current = brief.subtopics ?? [];
		const selected = current.includes(value)
			? current.filter((item) => item !== value)
			: current.length < 4
				? [...current, value]
				: current;
		brief = {
			...brief,
			subtopics: selected
		};
		clearValidation();
	}

	function handleAddCustomSubtopic() {
		if (!customSubtopic.trim()) return;
		handleSubtopicToggle(customSubtopic.trim());
		customSubtopic = '';
	}

	function continueSubtopics() {
		if (!(brief.subtopics?.length)) return;
		resetSupportSelections();
		moveToStep('choose_subtopic', nextStepAfterSubtopic());
	}

	function toggleLearnerChip(chip: string) {
		const nextChips = selectedLearnerChips.includes(chip)
			? selectedLearnerChips.filter((item) => item !== chip)
			: [...selectedLearnerChips, chip];
		selectedLearnerChips = nextChips;
		syncLearnerContext(learnerText, nextChips);
		clearValidation();
	}

	function continueLearnerContext() {
		if (!brief.learner_context?.trim()) return;
		updateSupportRecommendations();
		moveToStep('learner_context', 'intended_outcome');
	}

	function handleOutcomeSelect(value: TeacherBrief['intended_outcome']) {
		brief = {
			...brief,
			intended_outcome: value
		};
		updateSupportRecommendations();
		clearValidation();
		moveToStep('intended_outcome', 'resource_type');
	}

	function handleResourceTypeSelect(value: TeacherBrief['resource_type']) {
		brief = {
			...brief,
			resource_type: value
		};
		updateSupportRecommendations();
		clearValidation();
		moveToStep('resource_type', 'supports');
	}

	function toggleSupport(support: TeacherBriefSupport) {
		const current = brief.supports ?? [];
		brief = {
			...brief,
			supports: current.includes(support)
				? current.filter((item) => item !== support)
				: [...current, support]
		};
		clearValidation();
	}

	function continueSupports() {
		moveToStep('supports', 'depth');
	}

	function handleDepthSelect(value: TeacherBrief['depth']) {
		brief = {
			...brief,
			depth: value
		};
		clearValidation();
		moveToStep('depth', 'review');
	}

	async function handleValidate() {
		if (!reviewReady) return;
		loading = true;
		apiError = null;
		try {
			const result = await validateTeacherBrief({
				brief: brief as TeacherBrief
			});
			validationResult = result;
			warnings = [
				...result.blockers.map((item) => ({
					field: item.field,
					message: item.message,
					severity: 'blocking' as const
				})),
				...result.warnings.map((item) => ({
					field: item.field,
					message: item.message,
					severity: 'warning' as const
				}))
			];
			if (result.is_ready) {
				const review = await reviewTeacherBrief({
					brief: brief as TeacherBrief
				});
				reviewWarnings = review.warnings;
			}
			markStepCompleted('review');
		} catch (error) {
			apiError = error instanceof Error ? error.message : 'Brief validation failed.';
		} finally {
			loading = false;
		}
	}

	async function handlePlanFromBrief() {
		if (!validationResult?.is_ready) return;
		loading = true;
		apiError = null;
		stage = 'planning';
		try {
			plannedSpec = await planFromBrief(brief as TeacherBrief);
			stage = 'reviewing';
		} catch (error) {
			stage = 'building';
			apiError = error instanceof Error ? error.message : 'Planning failed.';
		} finally {
			loading = false;
		}
	}

	async function handleCommit() {
		if (!plannedSpec) return;
		loading = true;
		apiError = null;
		try {
			const accepted = await commitPlan(plannedSpec);
			acceptedGeneration = accepted;
			setGenerationAccepted(accepted);
			stage = 'generating';
		} catch (error) {
			apiError = error instanceof Error ? error.message : 'Failed to start generation.';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		resetGenerationState();
		void getProfile()
			.then((profile) => {
				if (learnerText.trim()) return;
				const seeded = [profile.default_audience_description, profile.classroom_context]
					.filter(Boolean)
					.join('. ')
					.trim();
				if (seeded) {
					syncLearnerContext(seeded);
				}
			})
			.catch(() => {
				// The builder works without profile hydration.
			});
	});
</script>

{#if stage === 'reviewing' && plannedSpec}
	<PlanReviewStep plan={plannedSpec} loading={loading} onBack={resetPlanStage} onCommit={handleCommit} />
{:else if stage === 'generating' && acceptedGeneration}
	<GenerationView accepted={acceptedGeneration} onReset={resetPlanStage} />
{:else}
	<section class="builder-shell">
		<header class="builder-header">
			<div>
				<p class="eyebrow">Studio</p>
				<h1>Teacher brief builder</h1>
			<p class="lede">
				Capture the teaching intent first, narrow the topic, choose the resource shape, then
				review the brief, approve the frozen plan, and generate only the selected components.
			</p>
			</div>
			<a href="/dashboard" class="dashboard-link">Back to dashboard</a>
		</header>

		{#if apiError}
			<p class="notice notice-error" role="alert">{apiError}</p>
		{/if}

		{#if stage === 'planning'}
			<p class="notice notice-info" role="status">Building a component plan from your brief...</p>
		{/if}

		<div class="builder-stack">
			<BriefStepCard
				title="Topic"
				stepLabel="Step 1"
				active={active_step === 'topic'}
				completed={completed_steps.includes('topic')}
				summary={stepSummary('topic', brief, learnerText, selectedLearnerChips)}
				onEdit={() => editStep('topic')}
			>
				<TopicInputStep
					value={rawTopic}
					loading={loading && active_step === 'topic'}
					statusMessage={topicStatusMessage}
					onInput={handleTopicInput}
					onSubmit={handleTopicSubmit}
				/>
			</BriefStepCard>

			{#if isVisible('choose_subtopic')}
				<BriefStepCard
					title="Subtopic"
					stepLabel="Step 2"
					active={active_step === 'choose_subtopic'}
					completed={completed_steps.includes('choose_subtopic')}
					summary={stepSummary('choose_subtopic', brief, learnerText, selectedLearnerChips)}
					onEdit={() => editStep('choose_subtopic')}
				>
					<SubtopicChoiceStep
						options={suggestions.subtopics ?? []}
						selected={brief.subtopics ?? []}
						customValue={customSubtopic}
						clarificationMessage={topicStatusMessage}
						onToggle={handleSubtopicToggle}
						onCustomChange={(value) => (customSubtopic = value)}
						onAddCustom={handleAddCustomSubtopic}
						onContinue={continueSubtopics}
					/>
				</BriefStepCard>
			{/if}

			{#if isVisible('learner_context')}
				<BriefStepCard
					title="Learner Context"
					stepLabel="Step 3"
					active={active_step === 'learner_context'}
					completed={completed_steps.includes('learner_context')}
					summary={stepSummary('learner_context', brief, learnerText, selectedLearnerChips)}
					onEdit={() => editStep('learner_context')}
				>
					<LearnerContextStep
						value={learnerText}
						availableChips={[...learnerContextChips]}
						selectedChips={selectedLearnerChips}
						onInput={(value) => {
							syncLearnerContext(value);
							clearValidation();
						}}
						onToggleChip={toggleLearnerChip}
						onContinue={continueLearnerContext}
					/>
				</BriefStepCard>
			{/if}

			{#if isVisible('intended_outcome')}
				<BriefStepCard
					title="Intended Outcome"
					stepLabel="Step 4"
					active={active_step === 'intended_outcome'}
					completed={completed_steps.includes('intended_outcome')}
					summary={stepSummary('intended_outcome', brief, learnerText, selectedLearnerChips)}
					onEdit={() => editStep('intended_outcome')}
				>
					<OutcomeStep selected={brief.intended_outcome} onSelect={handleOutcomeSelect} />
				</BriefStepCard>
			{/if}

			{#if isVisible('resource_type')}
				<BriefStepCard
					title="Resource Type"
					stepLabel="Step 5"
					active={active_step === 'resource_type'}
					completed={completed_steps.includes('resource_type')}
					summary={stepSummary('resource_type', brief, learnerText, selectedLearnerChips)}
					onEdit={() => editStep('resource_type')}
				>
					<ResourceTypeStep selected={brief.resource_type} onSelect={handleResourceTypeSelect} />
				</BriefStepCard>
			{/if}

			{#if isVisible('supports')}
				<BriefStepCard
					title="Supports"
					stepLabel="Step 6"
					active={active_step === 'supports'}
					completed={completed_steps.includes('supports')}
					summary={stepSummary('supports', brief, learnerText, selectedLearnerChips)}
					onEdit={() => editStep('supports')}
				>
					<SupportsStep
						selected={brief.supports ?? []}
						recommended={recommendedSupports}
						onToggle={toggleSupport}
						onContinue={continueSupports}
					/>
				</BriefStepCard>
			{/if}

			{#if isVisible('depth')}
				<BriefStepCard
					title="Depth"
					stepLabel="Step 7"
					active={active_step === 'depth'}
					completed={completed_steps.includes('depth')}
					summary={stepSummary('depth', brief, learnerText, selectedLearnerChips)}
					onEdit={() => editStep('depth')}
				>
					<DepthStep selected={brief.depth} onSelect={handleDepthSelect} />
				</BriefStepCard>
			{/if}

			{#if isVisible('review')}
				<BriefStepCard
					title="Review Brief"
					stepLabel="Step 8"
					active={active_step === 'review'}
					completed={completed_steps.includes('review')}
					summary={stepSummary('review', brief, learnerText, selectedLearnerChips)}
					onEdit={() => editStep('review')}
				>
					<BriefReviewCard
						brief={brief}
						learnerSummary={learnerSummary}
						validationResult={validationResult}
						warnings={warnings}
						reviewWarnings={reviewWarnings}
						validating={loading && active_step === 'review'}
						onValidate={handleValidate}
						onNotesInput={(value) => {
							brief = { ...brief, teacher_notes: value };
							clearValidation();
						}}
					/>

					{#if briefIsReady}
						<div class="review-actions">
							<button type="button" class="primary-action" onclick={handlePlanFromBrief} disabled={loading}>
								{loading ? 'Planning resource...' : 'Build plan'}
							</button>
						</div>
					{/if}
				</BriefStepCard>
			{/if}
		</div>
	</section>
{/if}

<style>
	.builder-shell {
		display: grid;
		gap: 1rem;
	}

	.builder-header {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
		align-items: start;
	}

	.eyebrow {
		margin: 0 0 0.35rem 0;
		font-size: 0.76rem;
		font-weight: 700;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: #6b7c88;
	}

	h1,
	p {
		margin: 0;
	}

	h1 {
		font-size: clamp(2rem, 3vw, 2.7rem);
	}

	.lede {
		margin-top: 0.45rem;
		max-width: 64ch;
		color: #625a50;
		line-height: 1.65;
	}

	.dashboard-link {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border-radius: 999px;
		padding: 0.45rem 0.8rem;
		font-size: 0.8rem;
		font-weight: 700;
		text-decoration: none;
		background: #f1ece4;
		color: #4f5c65;
	}

	.notice {
		margin: 0;
		border-radius: 0.95rem;
		padding: 0.85rem 0.95rem;
	}

	.notice-error {
		background: #fff2ee;
		color: #7d3524;
	}

	.notice-info {
		background: #eef8f4;
		color: #0b6a52;
	}

	.builder-stack {
		display: grid;
		gap: 1rem;
	}

	.review-actions {
		margin-top: 0.75rem;
		display: flex;
		justify-content: flex-end;
	}

	.primary-action {
		border: 0;
		border-radius: 999px;
		background: #1d9e75;
		color: white;
		padding: 0.8rem 1.1rem;
		font-weight: 700;
		cursor: pointer;
	}

	@media (max-width: 720px) {
		.builder-header {
			flex-direction: column;
			align-items: stretch;
		}

		.review-actions {
			justify-content: stretch;
		}
	}
</style>

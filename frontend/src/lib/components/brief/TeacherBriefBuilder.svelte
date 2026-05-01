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
		GRADE_BAND_BY_LEVEL,
		briefSteps,
		buildLearnerSummary,
		defaultClassProfile,
		recommendSupports,
		stepSummary
	} from '$lib/brief/config';
	import GenerationView from '$lib/components/studio/GenerationView.svelte';
	import PackComplete from '$lib/components/pack/PackComplete.svelte';
	import PackGenerating from '$lib/components/pack/PackGenerating.svelte';
	import PackReview from '$lib/components/pack/PackReview.svelte';
	import { planPackFromBrief, generatePack } from '$lib/api/learning-pack';
	import { resetGenerationState, setGenerationAccepted } from '$lib/stores/studio';
	import type {
		BriefBuilderStep,
		BriefReviewWarning,
		BriefValidationResult,
		BuilderWarning,
		ClassLearningPreference,
		ClassProfile,
		GenerationAccepted,
		PlanningGenerationSpec,
		TeacherBrief,
		TeacherBriefSupport,
		TeacherGradeLevel,
		TopicResolutionSubtopic
	} from '$lib/types';
	import type {
		LearningPackPlan,
		PackGenerateResponse,
		PackStatusResponse
	} from '$lib/types/learning-pack';

	import BriefReviewCard from './BriefReviewCard.svelte';
	import BriefStepCard from './BriefStepCard.svelte';
	import ClassProfileStep from './ClassProfileStep.svelte';
	import DepthStep from './DepthStep.svelte';
	import GradeLevelStep from './GradeLevelStep.svelte';
	import OutcomeStep from './OutcomeStep.svelte';
	import PlanReviewStep from './PlanReviewStep.svelte';
	import ResourceTypeStep from './ResourceTypeStep.svelte';
	import SubtopicChoiceStep from './SubtopicChoiceStep.svelte';
	import SupportsStep from './SupportsStep.svelte';
	import TopicInputStep from './TopicInputStep.svelte';

	type BuilderStage =
		| 'building'
		| 'planning'
		| 'reviewing'
		| 'generating'
		| 'pack-reviewing'
		| 'pack-generating'
		| 'pack-complete';

	let stage = $state<BuilderStage>('building');
	let active_step = $state<BriefBuilderStep>('topic');
	let completed_steps = $state<BriefBuilderStep[]>([]);
	let brief = $state<Partial<TeacherBrief>>({
		subtopics: [],
		supports: [],
		depth: 'standard',
		teacher_notes: '',
		class_profile: { ...defaultClassProfile }
	});
	let suggestions = $state<{ subtopics?: TopicResolutionSubtopic[] }>({});
	let warnings = $state<BuilderWarning[]>([]);
	let loading = $state(false);
	let validationResult = $state<BriefValidationResult | null>(null);
	let reviewWarnings = $state<BriefReviewWarning[]>([]);
	let rawTopic = $state('');
	let customSubtopic = $state('');
	let learnerText = $state('');
	let recommendedSupports = $state<TeacherBriefSupport[]>([]);
	let topicStatusMessage = $state<string | null>(null);
	let profileGradeBandHint = $state<string | null>(null);
	let apiError = $state<string | null>(null);
	let plannedSpec = $state<PlanningGenerationSpec | null>(null);
	let acceptedGeneration = $state<GenerationAccepted | null>(null);
	let packPlan = $state<LearningPackPlan | null>(null);
	let packResponse = $state<PackGenerateResponse | null>(null);
	let packStatus = $state<PackStatusResponse | null>(null);
	let packError = $state<string | null>(null);

	const learnerSummary = $derived(learnerText);
	const reviewReady = $derived(
		Boolean(
			brief.subject &&
				brief.topic &&
				brief.subtopics?.length &&
				brief.grade_level &&
				brief.grade_band &&
				brief.learner_context &&
				brief.intended_outcome &&
				brief.resource_type &&
				brief.depth
		)
	);
	const briefIsReady = $derived(Boolean(validationResult?.is_ready));

	function currentClassProfile(): ClassProfile {
		return { ...defaultClassProfile, ...(brief.class_profile ?? {}) };
	}

	function deriveRecommendedSupports(
		nextResourceType = brief.resource_type,
		nextOutcome = brief.intended_outcome,
		nextProfile = currentClassProfile()
	): TeacherBriefSupport[] {
		return recommendSupports({
			resourceType: nextResourceType,
			intendedOutcome: nextOutcome,
			classProfile: nextProfile
		});
	}

	function resetPlanStage() {
		stage = 'building';
		plannedSpec = null;
		acceptedGeneration = null;
		packPlan = null;
		packResponse = null;
		packStatus = null;
		packError = null;
		resetGenerationState();
	}

	function clearValidation() {
		validationResult = null;
		warnings = [];
		reviewWarnings = [];
		apiError = null;
	}

	function clearValidationAndGeneratedState() {
		clearValidation();
		if (stage !== 'building') {
			resetPlanStage();
		}
	}

	function titleCase(value: string): string {
		return value
			.split('_')
			.map((part) => part.charAt(0).toUpperCase() + part.slice(1))
			.join(' ');
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

	function syncAudience({
		gradeLevel = brief.grade_level,
		classProfile = currentClassProfile(),
		learnerSummaryOverride,
		recomputeSupports = true
	}: {
		gradeLevel?: TeacherGradeLevel;
		classProfile?: ClassProfile;
		learnerSummaryOverride?: string;
		recomputeSupports?: boolean;
	}) {
		const gradeBand = gradeLevel ? GRADE_BAND_BY_LEVEL[gradeLevel] : brief.grade_band;
		const nextSummary =
			learnerSummaryOverride ?? buildLearnerSummary({ gradeLevel, classProfile });
		const supports = recomputeSupports
			? deriveRecommendedSupports(brief.resource_type, brief.intended_outcome, classProfile)
			: (brief.supports ?? []);

		learnerText = nextSummary;
		recommendedSupports = deriveRecommendedSupports(
			brief.resource_type,
			brief.intended_outcome,
			classProfile
		);
		brief = {
			...brief,
			grade_level: gradeLevel,
			grade_band: gradeBand,
			class_profile: classProfile,
			learner_context: nextSummary,
			supports
		};
		clearValidationAndGeneratedState();
	}

	function clearSubtopicResolutionState() {
		suggestions = {};
		customSubtopic = '';
		topicStatusMessage = null;
		brief = {
			...brief,
			subject: '',
			topic: '',
			subtopics: []
		};
		completed_steps = completed_steps.filter(
			(step) => !['choose_subtopic', 'review'].includes(step)
		);
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
		clearSubtopicResolutionState();
		clearValidationAndGeneratedState();
	}

	function handleTopicInput(value: string) {
		rawTopic = value;
		if (brief.topic && value.trim() && value.trim() !== brief.topic) {
			resetAfterTopicChange();
		}
	}

	function handleTopicSubmit() {
		if (!rawTopic.trim()) return;
		const normalizedRawTopic = rawTopic.trim();
		apiError = null;
		rawTopic = normalizedRawTopic;
		clearSubtopicResolutionState();
		brief = {
			...brief,
			topic: normalizedRawTopic
		};
		clearValidationAndGeneratedState();
		moveToStep('topic', 'grade_level');
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
		moveToStep('choose_subtopic', 'class_profile');
	}

	async function handleGradeLevelSelect(value: TeacherGradeLevel) {
		const nextProfile = currentClassProfile();
		const nextGradeBand = GRADE_BAND_BY_LEVEL[value];
		const nextSummary = buildLearnerSummary({
			gradeLevel: value,
			classProfile: nextProfile
		});

		syncAudience({
			gradeLevel: value,
			classProfile: nextProfile,
			learnerSummaryOverride: nextSummary
		});
		clearSubtopicResolutionState();

		if (!rawTopic.trim()) {
			return;
		}

		loading = true;
		apiError = null;
		topicStatusMessage = 'Finding grade-appropriate subtopics...';
		try {
			const result = await resolveTopic({
				raw_topic: rawTopic.trim(),
				grade_level: value,
				grade_band: nextGradeBand,
				learner_context: nextSummary || undefined,
				class_profile: nextProfile
			});
			brief = {
				...brief,
				subject: result.subject,
				topic: result.topic,
				subtopics: [],
				grade_level: value,
				grade_band: nextGradeBand,
				class_profile: nextProfile,
				learner_context: nextSummary
			};
			suggestions = { subtopics: result.candidate_subtopics };
			customSubtopic = '';
			topicStatusMessage = result.clarification_message ?? null;
			moveToStep('grade_level', 'choose_subtopic');
		} catch (error) {
			apiError = error instanceof Error ? error.message : 'Topic resolution failed.';
			topicStatusMessage = null;
		} finally {
			loading = false;
		}
	}

	function updateClassProfile(nextProfile: ClassProfile) {
		syncAudience({
			gradeLevel: brief.grade_level,
			classProfile: nextProfile
		});
	}

	function togglePreference(preference: ClassLearningPreference) {
		const profile = currentClassProfile();
		const nextPreferences = profile.learning_preferences.includes(preference)
			? profile.learning_preferences.filter((item) => item !== preference)
			: [...profile.learning_preferences, preference];
		updateClassProfile({
			...profile,
			learning_preferences: nextPreferences
		});
	}

	function continueClassProfile() {
		if (!brief.learner_context?.trim()) return;
		moveToStep('class_profile', 'intended_outcome');
	}

	function handleOutcomeSelect(value: TeacherBrief['intended_outcome']) {
		const nextProfile = currentClassProfile();
		recommendedSupports = deriveRecommendedSupports(brief.resource_type, value, nextProfile);
		brief = {
			...brief,
			intended_outcome: value,
			supports: recommendedSupports
		};
		clearValidationAndGeneratedState();
		moveToStep('intended_outcome', 'resource_type');
	}

	function handleResourceTypeSelect(value: TeacherBrief['resource_type']) {
		const nextProfile = currentClassProfile();
		recommendedSupports = deriveRecommendedSupports(value, brief.intended_outcome, nextProfile);
		brief = {
			...brief,
			resource_type: value,
			supports: recommendedSupports
		};
		clearValidationAndGeneratedState();
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

	async function handleGenerateAsPack() {
		if (!plannedSpec) return;
		loading = true;
		packError = null;
		try {
			packPlan = await planPackFromBrief(plannedSpec.source_brief);
			stage = 'pack-reviewing';
		} catch (err) {
			packError = err instanceof Error ? err.message : 'Could not plan pack.';
		} finally {
			loading = false;
		}
	}

	async function handlePackConfirmed(editedPlan: LearningPackPlan) {
		if (!plannedSpec) return;
		loading = true;
		packError = null;
		try {
			packResponse = await generatePack(editedPlan, plannedSpec.source_brief.learner_context);
			stage = 'pack-generating';
		} catch (err) {
			packError = err instanceof Error ? err.message : 'Could not start pack generation.';
		} finally {
			loading = false;
		}
	}

	function handlePackComplete(status: PackStatusResponse) {
		packStatus = status;
		stage = 'pack-complete';
	}

	function resetPackState() {
		packPlan = null;
		packResponse = null;
		packStatus = null;
		packError = null;
		stage = 'reviewing';
	}

	onMount(() => {
		resetGenerationState();
		void getProfile()
			.then((profile) => {
				profileGradeBandHint = titleCase(profile.default_grade_band);
				if (currentClassProfile().notes?.trim()) return;
				brief = {
					...brief,
					class_profile: {
						...currentClassProfile(),
						notes: profile.classroom_context || currentClassProfile().notes
					}
				};
			})
			.catch(() => {
				// The builder works without profile hydration.
			});
	});
</script>

{#if stage === 'reviewing' && plannedSpec}
	<PlanReviewStep
		plan={plannedSpec}
		loading={loading}
		onBack={resetPlanStage}
		onCommit={handleCommit}
		onGenerateAsPack={handleGenerateAsPack}
		packError={packError}
	/>
{:else if stage === 'generating' && acceptedGeneration}
	<GenerationView accepted={acceptedGeneration} onReset={resetPlanStage} />
{:else if stage === 'pack-reviewing' && packPlan}
	<PackReview
		plan={packPlan}
		generating={loading}
		error={packError}
		onBack={resetPackState}
		onConfirmed={handlePackConfirmed}
	/>
{:else if stage === 'pack-generating' && packResponse}
	<PackGenerating packId={packResponse.pack_id} onComplete={handlePackComplete} />
{:else if stage === 'pack-complete' && packStatus}
	<PackComplete packStatus={packStatus} onNewPack={resetPlanStage} />
{:else}
	<section class="builder-shell">
		<header class="builder-header">
			<div>
				<p class="eyebrow">Studio</p>
				<h1>Teacher brief builder</h1>
			<p class="lede">
				Capture the teaching intent first, narrow the topic, profile the class, choose the
				resource shape, then review the brief, approve the frozen plan, and generate only the
				selected components.
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
				summary={stepSummary('topic', brief, learnerText)}
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

			{#if isVisible('grade_level')}
				<BriefStepCard
					title="Grade Level"
					stepLabel="Step 2"
					active={active_step === 'grade_level'}
					completed={completed_steps.includes('grade_level')}
					summary={stepSummary('grade_level', brief, learnerText)}
					onEdit={() => editStep('grade_level')}
				>
					<GradeLevelStep
						selected={brief.grade_level}
						derivedBand={brief.grade_band ?? null}
						defaultGradeBandHint={profileGradeBandHint}
						statusMessage={loading && active_step === 'grade_level' ? topicStatusMessage : null}
						loading={loading && active_step === 'grade_level'}
						onSelect={handleGradeLevelSelect}
					/>
				</BriefStepCard>
			{/if}

			{#if isVisible('choose_subtopic')}
				<BriefStepCard
					title="Subtopic"
					stepLabel="Step 3"
					active={active_step === 'choose_subtopic'}
					completed={completed_steps.includes('choose_subtopic')}
					summary={stepSummary('choose_subtopic', brief, learnerText)}
					onEdit={() => editStep('choose_subtopic')}
				>
					<SubtopicChoiceStep
						options={suggestions.subtopics ?? []}
						selected={brief.subtopics ?? []}
						customValue={customSubtopic}
						selectedGradeLevel={brief.grade_level}
						clarificationMessage={topicStatusMessage}
						onToggle={handleSubtopicToggle}
						onCustomChange={(value) => (customSubtopic = value)}
						onAddCustom={handleAddCustomSubtopic}
						onContinue={continueSubtopics}
					/>
				</BriefStepCard>
			{/if}

			{#if isVisible('class_profile')}
				<BriefStepCard
					title="Class Profile"
					stepLabel="Step 4"
					active={active_step === 'class_profile'}
					completed={completed_steps.includes('class_profile')}
					summary={stepSummary('class_profile', brief, learnerText)}
					onEdit={() => editStep('class_profile')}
				>
					<ClassProfileStep
						profile={currentClassProfile()}
						summary={learnerText}
						onReadingLevelChange={(value) =>
							updateClassProfile({ ...currentClassProfile(), reading_level: value })}
						onLanguageSupportChange={(value) =>
							updateClassProfile({ ...currentClassProfile(), language_support: value })}
						onConfidenceChange={(value) =>
							updateClassProfile({ ...currentClassProfile(), confidence: value })}
						onPriorKnowledgeChange={(value) =>
							updateClassProfile({ ...currentClassProfile(), prior_knowledge: value })}
						onPacingChange={(value) =>
							updateClassProfile({ ...currentClassProfile(), pacing: value })}
						onPreferenceToggle={togglePreference}
						onNotesInput={(value) =>
							updateClassProfile({ ...currentClassProfile(), notes: value })}
						onSummaryInput={(value) =>
							syncAudience({
								gradeLevel: brief.grade_level,
								classProfile: currentClassProfile(),
								learnerSummaryOverride: value,
								recomputeSupports: false
							})}
						onContinue={continueClassProfile}
					/>
				</BriefStepCard>
			{/if}

			{#if isVisible('intended_outcome')}
				<BriefStepCard
					title="Intended Outcome"
					stepLabel="Step 5"
					active={active_step === 'intended_outcome'}
					completed={completed_steps.includes('intended_outcome')}
					summary={stepSummary('intended_outcome', brief, learnerText)}
					onEdit={() => editStep('intended_outcome')}
				>
					<OutcomeStep selected={brief.intended_outcome} onSelect={handleOutcomeSelect} />
				</BriefStepCard>
			{/if}

			{#if isVisible('resource_type')}
				<BriefStepCard
					title="Resource Type"
					stepLabel="Step 6"
					active={active_step === 'resource_type'}
					completed={completed_steps.includes('resource_type')}
					summary={stepSummary('resource_type', brief, learnerText)}
					onEdit={() => editStep('resource_type')}
				>
					<ResourceTypeStep selected={brief.resource_type} onSelect={handleResourceTypeSelect} />
				</BriefStepCard>
			{/if}

			{#if isVisible('supports')}
				<BriefStepCard
					title="Supports"
					stepLabel="Step 7"
					active={active_step === 'supports'}
					completed={completed_steps.includes('supports')}
					summary={stepSummary('supports', brief, learnerText)}
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
					stepLabel="Step 8"
					active={active_step === 'depth'}
					completed={completed_steps.includes('depth')}
					summary={stepSummary('depth', brief, learnerText)}
					onEdit={() => editStep('depth')}
				>
					<DepthStep selected={brief.depth} onSelect={handleDepthSelect} />
				</BriefStepCard>
			{/if}

			{#if isVisible('review')}
				<BriefStepCard
					title="Review Brief"
					stepLabel="Step 9"
					active={active_step === 'review'}
					completed={completed_steps.includes('review')}
					summary={stepSummary('review', brief, learnerText)}
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

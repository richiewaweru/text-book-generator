import type {
	BriefBuilderStep,
	TeacherBrief,
	TeacherBriefDepth,
	TeacherBriefOutcome,
	TeacherBriefResourceType,
	TeacherBriefSupport
} from '$lib/types';

export const briefSteps: BriefBuilderStep[] = [
	'topic',
	'choose_subtopic',
	'learner_context',
	'intended_outcome',
	'resource_type',
	'supports',
	'depth',
	'review'
];

export const learnerContextChips = [
	'English learners',
	'Below grade level',
	'Advanced students',
	'IEP supports',
	'Visual learners',
	'Low confidence',
	'Mixed ability'
] as const;

export const outcomeOptions: Array<{
	value: TeacherBriefOutcome;
	label: string;
	description: string;
}> = [
	{
		value: 'understand',
		label: 'Understand the idea',
		description: 'Prioritize explanation, examples, and quick checks.'
	},
	{
		value: 'practice',
		label: 'Practice a skill',
		description: 'Focus on modeling, repetition, and guided support.'
	},
	{
		value: 'review',
		label: 'Review before a quiz',
		description: 'Mix recap, short checks, and quick retrieval.'
	},
	{
		value: 'assess',
		label: 'Show understanding',
		description: 'Use assessment-style prompts and evidence of learning.'
	},
	{
		value: 'compare',
		label: 'Compare ideas',
		description: 'Frame contrasts, examples, and reflective checks.'
	},
	{
		value: 'vocabulary',
		label: 'Build vocabulary',
		description: 'Teach and reinforce key terms in context.'
	}
];

export const resourceTypeOptions: Array<{
	value: TeacherBriefResourceType;
	label: string;
	description: string;
}> = [
	{
		value: 'worksheet',
		label: 'Worksheet',
		description: 'Short instruction plus student work.'
	},
	{
		value: 'mini_booklet',
		label: 'Mini-booklet',
		description: 'Guided learning students can follow step by step.'
	},
	{
		value: 'exit_ticket',
		label: 'Exit ticket',
		description: 'Quick end-of-lesson check.'
	},
	{
		value: 'quick_explainer',
		label: 'Quick explainer',
		description: 'Focused concept clarification or reference.'
	},
	{
		value: 'practice_set',
		label: 'Practice set',
		description: 'Mostly questions and repetition.'
	},
	{
		value: 'quiz',
		label: 'Quiz',
		description: 'Assessment-style questions and checks.'
	}
];

export const supportOptions: Array<{
	value: TeacherBriefSupport;
	label: string;
}> = [
	{ value: 'visuals', label: 'Visuals' },
	{ value: 'vocabulary_support', label: 'Vocabulary help' },
	{ value: 'worked_examples', label: 'Worked examples' },
	{ value: 'step_by_step', label: 'Step-by-step hints' },
	{ value: 'discussion_questions', label: 'Discussion questions' },
	{ value: 'simpler_reading', label: 'Simpler reading' },
	{ value: 'challenge_questions', label: 'Challenge questions' }
];

export const depthOptions: Array<{
	value: TeacherBriefDepth;
	label: string;
	description: string;
}> = [
	{ value: 'quick', label: 'Quick', description: '5-10 minutes' },
	{ value: 'standard', label: 'Standard', description: '20-30 minutes' },
	{ value: 'deep', label: 'Deep', description: '40-60 minutes' }
];

const supportPriorityMatrix: Record<
	TeacherBriefResourceType,
	Partial<Record<TeacherBriefOutcome, TeacherBriefSupport[]>>
> = {
	worksheet: {
		understand: ['visuals', 'worked_examples'],
		practice: ['worked_examples', 'step_by_step'],
		review: ['worked_examples'],
		assess: ['visuals'],
		compare: ['discussion_questions', 'visuals'],
		vocabulary: ['vocabulary_support', 'visuals']
	},
	mini_booklet: {
		understand: ['visuals', 'vocabulary_support'],
		practice: ['step_by_step', 'worked_examples'],
		review: ['visuals', 'discussion_questions'],
		assess: ['visuals'],
		compare: ['discussion_questions', 'visuals'],
		vocabulary: ['vocabulary_support', 'simpler_reading']
	},
	exit_ticket: {
		practice: ['step_by_step'],
		review: ['discussion_questions'],
		assess: [],
		compare: ['discussion_questions']
	},
	quick_explainer: {
		understand: ['visuals'],
		review: ['visuals'],
		compare: ['visuals'],
		vocabulary: ['vocabulary_support']
	},
	practice_set: {
		practice: ['worked_examples', 'step_by_step'],
		review: ['worked_examples'],
		assess: [],
		vocabulary: ['vocabulary_support']
	},
	quiz: {
		assess: [],
		review: [],
		vocabulary: ['vocabulary_support'],
		practice: []
	}
};

export function buildLearnerContext(text: string, chips: string[]): string {
	const trimmed = text.trim();
	if (chips.length === 0) {
		return trimmed;
	}
	const suffix = `Focus tags: ${chips.join(', ')}.`;
	return trimmed ? `${trimmed}\n${suffix}` : suffix;
}

function hasAny(text: string, phrases: string[]): boolean {
	const normalized = text.toLowerCase();
	return phrases.some((phrase) => normalized.includes(phrase));
}

export function recommendSupports({
	resourceType,
	intendedOutcome,
	learnerContext,
	learnerChips
}: {
	resourceType?: TeacherBriefResourceType;
	intendedOutcome?: TeacherBriefOutcome;
	learnerContext: string;
	learnerChips: string[];
}): TeacherBriefSupport[] {
	if (!resourceType || !intendedOutcome) {
		return [];
	}

	const recommended = new Set<TeacherBriefSupport>(
		supportPriorityMatrix[resourceType][intendedOutcome] ?? []
	);
	const normalizedChips = learnerChips.map((chip) => chip.toLowerCase());
	const normalizedContext = learnerContext.toLowerCase();

	if (
		normalizedChips.includes('visual learners') ||
		hasAny(normalizedContext, ['visual', 'diagram', 'image'])
	) {
		recommended.add('visuals');
	}

	if (
		normalizedChips.includes('english learners') ||
		hasAny(normalizedContext, ['english learner', 'ell', 'vocabulary'])
	) {
		recommended.add('vocabulary_support');
		recommended.add('simpler_reading');
	}

	if (
		normalizedChips.includes('below grade level') ||
		normalizedChips.includes('low confidence') ||
		normalizedChips.includes('iep supports') ||
		hasAny(normalizedContext, ['struggle', 'below grade', 'low confidence'])
	) {
		recommended.add('step_by_step');
	}

	if (intendedOutcome === 'practice' && resourceType !== 'quiz' && resourceType !== 'exit_ticket') {
		recommended.add('worked_examples');
	}

	if (normalizedChips.includes('advanced students')) {
		recommended.add('challenge_questions');
	}

	if (intendedOutcome === 'compare') {
		recommended.add('discussion_questions');
	}

	if (resourceType === 'quiz' || resourceType === 'exit_ticket') {
		recommended.delete('worked_examples');
	}

	return Array.from(recommended);
}

export function stepSummary(
	step: BriefBuilderStep,
	brief: Partial<TeacherBrief>,
	learnerText: string,
	learnerChips: string[]
): string {
	switch (step) {
		case 'topic':
		case 'choose_subtopic':
			if (brief.subject && brief.topic && brief.subtopic) {
				return `${brief.subject} -> ${brief.topic} -> ${brief.subtopic}`;
			}
			if (brief.subject && brief.topic) {
				return `${brief.subject} -> ${brief.topic}`;
			}
			return brief.topic ?? 'Not set';
		case 'learner_context':
			return learnerText || learnerChips.join(', ') || 'Not set';
		case 'intended_outcome':
			return (
				outcomeOptions.find((option) => option.value === brief.intended_outcome)?.label ??
				'Not set'
			);
		case 'resource_type':
			return (
				resourceTypeOptions.find((option) => option.value === brief.resource_type)?.label ??
				'Not set'
			);
		case 'supports':
			return brief.supports?.length
				? brief.supports
						.map((support) => supportOptions.find((option) => option.value === support)?.label ?? support)
						.join(', ')
				: 'No extra supports selected';
		case 'depth':
			return depthOptions.find((option) => option.value === brief.depth)?.label ?? 'Not set';
		case 'review':
			return 'Ready to validate';
	}
}

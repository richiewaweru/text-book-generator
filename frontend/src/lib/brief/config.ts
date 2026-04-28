import type {
	BriefBuilderStep,
	ClassConfidence,
	ClassLanguageSupport,
	ClassLearningPreference,
	ClassPacing,
	ClassPriorKnowledge,
	ClassProfile,
	ClassReadingLevel,
	TeacherBrief,
	TeacherBriefDepth,
	TeacherBriefOutcome,
	TeacherBriefResourceType,
	TeacherBriefSupport,
	TeacherGradeBand,
	TeacherGradeLevel
} from '$lib/types';

export const briefSteps: BriefBuilderStep[] = [
	'topic',
	'choose_subtopic',
	'grade_level',
	'class_profile',
	'intended_outcome',
	'resource_type',
	'supports',
	'depth',
	'review'
];

export const GRADE_BAND_BY_LEVEL: Record<TeacherGradeLevel, TeacherGradeBand> = {
	pre_k: 'early_elementary',
	kindergarten: 'early_elementary',
	grade_1: 'early_elementary',
	grade_2: 'early_elementary',
	grade_3: 'upper_elementary',
	grade_4: 'upper_elementary',
	grade_5: 'upper_elementary',
	grade_6: 'middle_school',
	grade_7: 'middle_school',
	grade_8: 'middle_school',
	grade_9: 'high_school',
	grade_10: 'high_school',
	grade_11: 'high_school',
	grade_12: 'high_school',
	college: 'college',
	adult: 'adult',
	mixed: 'mixed'
};

export const gradeLevelOptions: Array<{
	value: TeacherGradeLevel;
	label: string;
	description: string;
}> = [
	{ value: 'pre_k', label: 'Pre-K', description: 'Very early learners who need concrete language and visuals.' },
	{ value: 'kindergarten', label: 'Kindergarten', description: 'Early readers who benefit from short, highly supported directions.' },
	{ value: 'grade_1', label: 'Grade 1', description: 'Primary learners with short chunks and concrete examples.' },
	{ value: 'grade_2', label: 'Grade 2', description: 'Primary learners ready for guided practice and simple text.' },
	{ value: 'grade_3', label: 'Grade 3', description: 'Upper elementary learners moving into more independent reading.' },
	{ value: 'grade_4', label: 'Grade 4', description: 'Upper elementary learners balancing visuals with short explanations.' },
	{ value: 'grade_5', label: 'Grade 5', description: 'Upper elementary learners preparing for longer reasoning tasks.' },
	{ value: 'grade_6', label: 'Grade 6', description: 'Middle school learners who often need concrete setup and structure.' },
	{ value: 'grade_7', label: 'Grade 7', description: 'Middle school learners ready for guided explanation plus practice.' },
	{ value: 'grade_8', label: 'Grade 8', description: 'Middle school learners who can handle more abstraction with support.' },
	{ value: 'grade_9', label: 'Grade 9', description: 'High school learners transitioning into subject-specific vocabulary.' },
	{ value: 'grade_10', label: 'Grade 10', description: 'High school learners who can balance explanation and independent work.' },
	{ value: 'grade_11', label: 'Grade 11', description: 'High school learners often ready for more precise reasoning.' },
	{ value: 'grade_12', label: 'Grade 12', description: 'High school learners preparing for college-level expectations.' },
	{ value: 'college', label: 'College', description: 'Post-secondary learners who can handle dense content and precision.' },
	{ value: 'adult', label: 'Adult', description: 'Adult learners who may need direct, relevant, practical framing.' },
	{ value: 'mixed', label: 'Mixed grades', description: 'A deliberately mixed group where the plan should stay adaptable.' }
];

export const readingLevelOptions: Array<{
	value: ClassReadingLevel;
	label: string;
	description: string;
}> = [
	{ value: 'below_grade', label: 'Below grade level', description: 'Shorter reading load and simpler syntax.' },
	{ value: 'on_grade', label: 'At grade level', description: 'Typical text load for the selected grade.' },
	{ value: 'above_grade', label: 'Above grade level', description: 'Can handle denser text and challenge.' },
	{ value: 'mixed', label: 'Mixed reading levels', description: 'Need flexibility across support levels.' }
];

export const languageSupportOptions: Array<{
	value: ClassLanguageSupport;
	label: string;
	description: string;
}> = [
	{ value: 'none', label: 'Minimal language support', description: 'Most learners can access standard classroom language.' },
	{ value: 'some_ell', label: 'Some multilingual learners', description: 'Add vocabulary help and clearer wording.' },
	{ value: 'many_ell', label: 'Many multilingual learners', description: 'Lean into visuals, repetition, and plain language.' }
];

export const confidenceOptions: Array<{
	value: ClassConfidence;
	label: string;
	description: string;
}> = [
	{ value: 'low', label: 'Low confidence', description: 'Needs more modeled support and reassurance.' },
	{ value: 'mixed', label: 'Mixed confidence', description: 'Some learners need scaffolds while others move faster.' },
	{ value: 'high', label: 'High confidence', description: 'Learners can usually handle quicker release.' }
];

export const priorKnowledgeOptions: Array<{
	value: ClassPriorKnowledge;
	label: string;
	description: string;
}> = [
	{ value: 'new_topic', label: 'Brand new topic', description: 'Assume little background knowledge.' },
	{ value: 'some_background', label: 'Some background', description: 'Learners have partial familiarity.' },
	{ value: 'reviewing', label: 'Reviewing', description: 'Learners have already seen the idea before.' }
];

export const pacingOptions: Array<{
	value: ClassPacing;
	label: string;
	description: string;
}> = [
	{ value: 'short_chunks', label: 'Short chunks', description: 'Keep moves brief and highly scaffolded.' },
	{ value: 'normal', label: 'Normal pacing', description: 'Balanced pacing for a typical class period.' },
	{ value: 'can_handle_longer', label: 'Can handle longer stretches', description: 'Learners can sustain longer reading or practice blocks.' }
];

export const learningPreferenceOptions: Array<{
	value: ClassLearningPreference;
	label: string;
}> = [
	{ value: 'visual', label: 'Visual anchors' },
	{ value: 'step_by_step', label: 'Step-by-step support' },
	{ value: 'discussion', label: 'Discussion' },
	{ value: 'hands_on', label: 'Hands-on tasks' },
	{ value: 'independent', label: 'Independent work' },
	{ value: 'challenge', label: 'Challenge' }
];

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

export const defaultClassProfile: ClassProfile = {
	reading_level: 'mixed',
	language_support: 'none',
	confidence: 'mixed',
	prior_knowledge: 'some_background',
	pacing: 'normal',
	learning_preferences: [],
	notes: ''
};

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

function titleCase(value: string): string {
	return value
		.split('_')
		.map((part) => part.charAt(0).toUpperCase() + part.slice(1))
		.join(' ');
}

export function gradeBandLabel(band: TeacherGradeBand): string {
	return titleCase(band);
}

export function gradeLevelLabel(level: TeacherGradeLevel): string {
	return gradeLevelOptions.find((option) => option.value === level)?.label ?? titleCase(level);
}

export function buildLearnerSummary({
	gradeLevel,
	classProfile
}: {
	gradeLevel?: TeacherGradeLevel;
	classProfile: ClassProfile;
}): string {
	const parts: string[] = [];
	const gradeLabel = gradeLevel ? gradeLevelLabel(gradeLevel) : 'This class';
	parts.push(gradeLevel ? `${gradeLabel} learners` : gradeLabel);

	const readingMap: Record<ClassReadingLevel, string> = {
		below_grade: 'are reading below grade level',
		on_grade: 'are reading at grade level',
		above_grade: 'are reading above grade level',
		mixed: 'have mixed reading levels'
	};
	parts.push(readingMap[classProfile.reading_level]);

	const languageMap: Record<ClassLanguageSupport, string | null> = {
		none: null,
		some_ell: 'include some multilingual learners',
		many_ell: 'include many multilingual learners'
	};
	const languageSummary = languageMap[classProfile.language_support];
	if (languageSummary) {
		parts.push(languageSummary);
	}

	const priorKnowledgeMap: Record<ClassPriorKnowledge, string> = {
		new_topic: 'and are meeting this as a new topic',
		some_background: 'and have some background knowledge',
		reviewing: 'and are reviewing previously taught material'
	};
	parts.push(priorKnowledgeMap[classProfile.prior_knowledge]);

	const confidenceMap: Record<ClassConfidence, string> = {
		low: 'Confidence is low, so clear scaffolds will matter.',
		mixed: 'Confidence is mixed across the class.',
		high: 'Confidence is generally high.'
	};
	parts.push(confidenceMap[classProfile.confidence]);

	const pacingMap: Record<ClassPacing, string> = {
		short_chunks: 'Use short chunks and frequent checkpoints.',
		normal: 'A normal pacing should work well.',
		can_handle_longer: 'They can handle longer stretches of reading or practice.'
	};
	parts.push(pacingMap[classProfile.pacing]);

	if (classProfile.learning_preferences.length > 0) {
		const preferences = classProfile.learning_preferences.map((value) =>
			learningPreferenceOptions.find((option) => option.value === value)?.label.toLowerCase() ?? value
		);
		parts.push(`Helpful supports include ${preferences.join(', ')}.`);
	}

	if (classProfile.notes?.trim()) {
		parts.push(classProfile.notes.trim());
	}

	return parts.join(' ');
}

export function recommendSupports({
	resourceType,
	intendedOutcome,
	classProfile
}: {
	resourceType?: TeacherBriefResourceType;
	intendedOutcome?: TeacherBriefOutcome;
	classProfile: ClassProfile;
}): TeacherBriefSupport[] {
	if (!resourceType || !intendedOutcome) {
		return [];
	}

	const recommended = new Set<TeacherBriefSupport>(
		supportPriorityMatrix[resourceType][intendedOutcome] ?? []
	);

	if (
		classProfile.learning_preferences.includes('visual') ||
		classProfile.language_support === 'many_ell'
	) {
		recommended.add('visuals');
	}

	if (
		classProfile.language_support === 'some_ell' ||
		classProfile.language_support === 'many_ell'
	) {
		recommended.add('vocabulary_support');
		recommended.add('simpler_reading');
	}

	if (
		classProfile.reading_level === 'below_grade' ||
		classProfile.confidence === 'low' ||
		classProfile.pacing === 'short_chunks' ||
		classProfile.learning_preferences.includes('step_by_step')
	) {
		recommended.add('step_by_step');
	}

	if (
		intendedOutcome === 'practice' &&
		resourceType !== 'quiz' &&
		resourceType !== 'exit_ticket'
	) {
		recommended.add('worked_examples');
	}

	if (
		classProfile.reading_level === 'above_grade' ||
		classProfile.confidence === 'high' ||
		classProfile.learning_preferences.includes('challenge')
	) {
		recommended.add('challenge_questions');
	}

	if (classProfile.learning_preferences.includes('discussion') || intendedOutcome === 'compare') {
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
	learnerText: string
): string {
	switch (step) {
		case 'topic':
		case 'choose_subtopic':
			if (brief.subject && brief.topic && brief.subtopics?.length) {
				return `${brief.subject} -> ${brief.topic} -> ${brief.subtopics.join(', ')}`;
			}
			if (brief.subject && brief.topic) {
				return `${brief.subject} -> ${brief.topic}`;
			}
			return brief.topic ?? 'Not set';
		case 'grade_level':
			if (brief.grade_level && brief.grade_band) {
				return `${gradeLevelLabel(brief.grade_level)} -> ${gradeBandLabel(brief.grade_band)}`;
			}
			return brief.grade_level ? gradeLevelLabel(brief.grade_level) : 'Not set';
		case 'class_profile': {
			const profile = brief.class_profile;
			if (!profile) return learnerText || 'Not set';
			const preferences = profile.learning_preferences.length
				? profile.learning_preferences
						.map((value) => learningPreferenceOptions.find((option) => option.value === value)?.label ?? value)
						.join(', ')
				: 'No special preference';
			return `${titleCase(profile.reading_level)}, ${titleCase(profile.confidence)}, ${preferences}`;
		}
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

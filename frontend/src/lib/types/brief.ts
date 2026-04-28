export type TeacherBriefOutcome =
	| 'understand'
	| 'practice'
	| 'review'
	| 'assess'
	| 'compare'
	| 'vocabulary';

export type TeacherBriefResourceType =
	| 'worksheet'
	| 'mini_booklet'
	| 'exit_ticket'
	| 'quick_explainer'
	| 'practice_set'
	| 'quiz';

export type TeacherBriefSupport =
	| 'visuals'
	| 'vocabulary_support'
	| 'worked_examples'
	| 'step_by_step'
	| 'discussion_questions'
	| 'simpler_reading'
	| 'challenge_questions';

export type TeacherBriefDepth = 'quick' | 'standard' | 'deep';

export interface TeacherBrief {
	subject: string;
	topic: string;
	subtopics: string[];
	learner_context: string;
	intended_outcome: TeacherBriefOutcome;
	resource_type: TeacherBriefResourceType;
	supports: TeacherBriefSupport[];
	depth: TeacherBriefDepth;
	teacher_notes?: string | null;
}

export interface TopicResolutionRequest {
	raw_topic: string;
	learner_context?: string;
}

export interface TopicResolutionSubtopic {
	id: string;
	title: string;
	description: string;
	likely_grade_band?: string | null;
}

export interface TopicResolutionResult {
	subject: string;
	topic: string;
	candidate_subtopics: TopicResolutionSubtopic[];
	needs_clarification: boolean;
	clarification_message?: string | null;
}

export interface BriefValidationMessage {
	field?: string | null;
	message: string;
}

export interface BriefValidationSuggestion {
	field: string;
	suggestion: string;
}

export interface BriefValidationResult {
	is_ready: boolean;
	blockers: BriefValidationMessage[];
	warnings: BriefValidationMessage[];
	suggestions: BriefValidationSuggestion[];
}

export interface BriefValidationRequest {
	brief: TeacherBrief;
}

export interface BriefReviewRequest {
	brief: TeacherBrief;
}

export interface BriefReviewWarning {
	message: string;
	suggestion?: string | null;
}

export interface BriefReviewResult {
	coherent: boolean;
	warnings: BriefReviewWarning[];
}

export type BriefBuilderStep =
	| 'topic'
	| 'choose_subtopic'
	| 'learner_context'
	| 'intended_outcome'
	| 'resource_type'
	| 'supports'
	| 'depth'
	| 'review';

export interface BuilderWarning {
	field?: string | null;
	message: string;
	severity: 'warning' | 'blocking';
}

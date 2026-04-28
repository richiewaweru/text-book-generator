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

export type TeacherGradeLevel =
	| 'pre_k'
	| 'kindergarten'
	| 'grade_1'
	| 'grade_2'
	| 'grade_3'
	| 'grade_4'
	| 'grade_5'
	| 'grade_6'
	| 'grade_7'
	| 'grade_8'
	| 'grade_9'
	| 'grade_10'
	| 'grade_11'
	| 'grade_12'
	| 'college'
	| 'adult'
	| 'mixed';

export type TeacherGradeBand =
	| 'early_elementary'
	| 'upper_elementary'
	| 'middle_school'
	| 'high_school'
	| 'college'
	| 'adult'
	| 'mixed';

export type ClassReadingLevel = 'below_grade' | 'on_grade' | 'above_grade' | 'mixed';
export type ClassLanguageSupport = 'none' | 'some_ell' | 'many_ell';
export type ClassConfidence = 'low' | 'mixed' | 'high';
export type ClassPriorKnowledge = 'new_topic' | 'some_background' | 'reviewing';
export type ClassPacing = 'short_chunks' | 'normal' | 'can_handle_longer';
export type ClassLearningPreference =
	| 'visual'
	| 'step_by_step'
	| 'discussion'
	| 'hands_on'
	| 'independent'
	| 'challenge';

export interface ClassProfile {
	reading_level: ClassReadingLevel;
	language_support: ClassLanguageSupport;
	confidence: ClassConfidence;
	prior_knowledge: ClassPriorKnowledge;
	pacing: ClassPacing;
	learning_preferences: ClassLearningPreference[];
	notes?: string | null;
}

export interface TeacherBrief {
	subject: string;
	topic: string;
	subtopics: string[];
	grade_level: TeacherGradeLevel;
	grade_band: TeacherGradeBand;
	class_profile: ClassProfile;
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
	| 'grade_level'
	| 'class_profile'
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

import type { SectionContent } from 'lectio';
import type { PlanningGenerationSpec } from './studio';

export type Depth = 'survey' | 'standard' | 'deep';
export type GenerationMode = 'draft' | 'balanced' | 'strict';
export type NotationLanguage = 'plain' | 'math_notation' | 'python' | 'pseudocode';
export type EducationLevel =
	| 'elementary'
	| 'middle_school'
	| 'high_school'
	| 'undergraduate'
	| 'graduate'
	| 'professional';
export type LearningStyle = 'visual' | 'reading_writing' | 'kinesthetic' | 'auditory';

export interface User {
	id: string;
	email: string;
	name: string | null;
	picture_url: string | null;
	has_profile: boolean;
	created_at: string;
	updated_at: string;
}

export interface AuthResponse {
	access_token: string;
	token_type: string;
	user: User;
}

export interface StudentProfile {
	id: string;
	user_id: string;
	age: number;
	education_level: EducationLevel;
	interests: string[];
	learning_style: LearningStyle;
	preferred_notation: NotationLanguage;
	prior_knowledge: string;
	goals: string;
	preferred_depth: Depth;
	learner_description: string;
	created_at: string;
	updated_at: string;
}

export interface ProfileCreateRequest {
	age: number;
	education_level: EducationLevel;
	interests: string[];
	learning_style: LearningStyle;
	preferred_notation: NotationLanguage;
	prior_knowledge: string;
	goals: string;
	preferred_depth: Depth;
	learner_description: string;
}

export interface BriefRequest {
	intent: string;
	audience: string;
	extra_context: string;
}

export interface OutlineSection {
	section_id: string;
	position: number;
	title: string;
	focus: string;
}

export interface SectionPlan extends OutlineSection {
	role: string | null;
	required_components: string[];
	optional_components: string[];
	interaction_policy: string | null;
	diagram_policy: string | null;
	enrichment_enabled: boolean;
	continuity_notes: string | null;
}

export interface GenerationSpec {
	template_id: string;
	preset_id: string;
	mode: GenerationMode;
	section_count: number;
	sections: SectionPlan[];
	warning: string | null;
	rationale: string;
	source_brief: BriefRequest;
}

export type BriefResponse = GenerationSpec;

export interface GenerationRequest {
	subject: string;
	context: string;
	mode: GenerationMode;
	template_id: string;
	preset_id: string;
	section_count?: number;
	generation_spec?: GenerationSpec | null;
}

export interface EnhanceGenerationRequest {
	scope?: 'document' | 'section' | 'component';
	section_id?: string;
	component?: string;
	mode: Exclude<GenerationMode, 'draft'>;
	note?: string;
}

export interface GenerationAccepted {
	generation_id: string;
	status: string;
	mode: GenerationMode;
	source_generation_id?: string;
	events_url: string;
	document_url: string;
	report_url?: string;
}

export interface GenerationHistoryItem {
	id: string;
	subject: string;
	status: 'pending' | 'running' | 'completed' | 'failed';
	mode: GenerationMode;
	source_generation_id: string | null;
	error_type: string | null;
	error_code: string | null;
	requested_template_id: string;
	resolved_template_id: string | null;
	requested_preset_id: string;
	resolved_preset_id: string | null;
	section_count: number | null;
	quality_passed: boolean | null;
	generation_time_seconds: number | null;
	created_at: string | null;
	completed_at: string | null;
}

export interface GenerationDetail {
	id: string;
	subject: string;
	context: string;
	status: 'pending' | 'running' | 'completed' | 'failed';
	mode: GenerationMode;
	source_generation_id: string | null;
	error: string | null;
	error_type: string | null;
	error_code: string | null;
	requested_template_id: string;
	resolved_template_id: string | null;
	requested_preset_id: string;
	resolved_preset_id: string | null;
	section_count: number | null;
	quality_passed: boolean | null;
	generation_time_seconds: number | null;
	created_at: string | null;
	completed_at: string | null;
	document_path: string | null;
	planning_spec: GenerationSpec | PlanningGenerationSpec | null;
}

export interface PipelineSectionManifestItem {
	section_id: string;
	title: string;
	position: number;
}

export interface NodeFailureDetail {
	node: string;
	section_id: string;
	timestamp: string;
	error_type: string;
	error_message: string;
	retry_attempt: number;
	will_retry: boolean;
}

export interface FailedSectionEntry {
	section_id: string;
	title: string;
	position: number;
	focus?: string | null;
	bridges_from?: string | null;
	bridges_to?: string | null;
	needs_diagram: boolean;
	needs_worked_example: boolean;
	failed_at_node: string;
	error_type: string;
	error_summary: string;
	attempt_count: number;
	can_retry: boolean;
	missing_components: string[];
	failure_detail?: NodeFailureDetail | null;
}

export interface GenerationIssue {
	block: string;
	severity: 'blocking' | 'warning';
	message: string;
}

export interface GenerationSectionReport {
	section_id: string;
	passed: boolean;
	issues: GenerationIssue[];
	warnings: string[];
}

export interface GenerationDocument {
	generation_id: string;
	subject: string;
	context: string;
	mode: GenerationMode;
	template_id: string;
	preset_id: string;
	source_generation_id: string | null;
	status: 'pending' | 'running' | 'completed' | 'failed';
	section_manifest: PipelineSectionManifestItem[];
	sections: SectionContent[];
	failed_sections: FailedSectionEntry[];
	qc_reports: GenerationSectionReport[];
	quality_passed: boolean | null;
	error: string | null;
	created_at: string;
	updated_at: string;
	completed_at: string | null;
}

export interface PipelineStartEvent {
	type: 'pipeline_start';
	generation_id: string;
	section_count: number;
	template_id: string;
	preset_id: string;
	mode: GenerationMode;
	started_at: string;
}

export interface SectionStartedEvent {
	type: 'section_started';
	generation_id: string;
	section_id: string;
	title: string;
	position: number;
}

export interface SectionReadyEvent {
	type: 'section_ready';
	generation_id: string;
	section_id: string;
	section: SectionContent;
	completed_sections: number;
	total_sections: number;
}

export interface SectionFailedEvent {
	type: 'section_failed';
	generation_id: string;
	section_id: string;
	title: string;
	position: number;
	failed_at_node: string;
	error_type: string;
	error_summary: string;
	focus?: string | null;
	bridges_from?: string | null;
	bridges_to?: string | null;
	needs_diagram: boolean;
	needs_worked_example: boolean;
	attempt_count: number;
	can_retry: boolean;
	missing_components: string[];
	failure_detail?: NodeFailureDetail | null;
	timestamp: string;
}

export interface QCCompleteEvent {
	type: 'qc_complete';
	generation_id: string;
	passed: number;
	total: number;
}

export type ProgressUpdateStage =
	| 'planning'
	| 'generating_section'
	| 'generating_diagram'
	| 'checking_quality'
	| 'repairing'
	| 'finalizing'
	| 'complete'
	| 'failed';

export interface ProgressUpdateEvent {
	type: 'progress_update';
	generation_id: string;
	stage: ProgressUpdateStage;
	label: string;
	section_id?: string | null;
}

export interface CompleteEvent {
	type: 'complete';
	generation_id: string;
	document_url?: string;
	report_url?: string;
	completed_at: string;
}

export interface ErrorEvent {
	type: 'error';
	generation_id: string;
	message: string;
	report_url?: string;
	completed_at: string;
}

export type GenerationStreamEvent =
	| PipelineStartEvent
	| SectionStartedEvent
	| SectionReadyEvent
	| SectionFailedEvent
	| QCCompleteEvent
	| ProgressUpdateEvent
	| CompleteEvent
	| ErrorEvent;

export type {
	Brevity,
	ClassStyle,
	DeliveryPreferences,
	ExplanationStyle,
	GenerationDirectives,
	LearningOutcome,
	LessonFormat,
	PlanningCompleteEvent,
	PlanningErrorEvent,
	PlanningGenerationSpec,
	PlanningSectionPlan,
	PlanningSectionPlannedEvent,
	PlanningStreamEvent,
	PlanningTemplateSelectedEvent,
	PlanDraft,
	ReadingLevel,
	SectionGenerationNotes,
	SectionRole,
	StudioBriefRequest,
	StudioGenerationState,
	StudioState,
	StudioTemplateContract,
	TeacherConstraints,
	TeacherSignals,
	TemplateAlternative,
	TemplateDecision,
	TopicType,
	Tone,
	UserBriefDraft,
	VisualPolicy
} from './studio';

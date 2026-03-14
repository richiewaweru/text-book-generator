/** Mirrors backend Pydantic schemas for type safety. */

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

export interface GenerationRequest {
	subject: string;
	context: string;
	depth?: Depth;
	language?: NotationLanguage;
	mode?: GenerationMode;
	provider?: string;
}

export interface EnhanceGenerationRequest {
	target_mode: Exclude<GenerationMode, 'draft'>;
	note?: string;
}

export interface GenerationResponse {
	textbook_id: string;
	mode: GenerationMode;
	quality_report: QualityReport | null;
	generation_time_seconds: number;
	quality_reruns: number;
	source_generation_id: string | null;
}

export interface GenerationProgress {
	mode: GenerationMode;
	phase: 'planning' | 'generating' | 'checking' | 'fixing' | 'rendering';
	message: string;
	sections_total: number | null;
	sections_completed: number;
	current_section_id: string | null;
	current_section_title: string | null;
	retry_attempt: number | null;
	retry_limit: number | null;
	flagged_section_ids: string[];
}

export interface GenerationStatus {
	id: string;
	status: 'pending' | 'running' | 'completed' | 'failed';
	mode: GenerationMode | null;
	progress: GenerationProgress | null;
	result: GenerationResponse | null;
	error: string | null;
	error_type: string | null;
	source_generation_id: string | null;
}

export interface GenerationHistoryItem {
	id: string;
	subject: string;
	status: 'pending' | 'running' | 'completed' | 'failed';
	mode: GenerationMode;
	source_generation_id: string | null;
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
	quality_passed: boolean | null;
	generation_time_seconds: number | null;
	created_at: string | null;
	completed_at: string | null;
}

export interface QualityIssue {
	section_id: string | null;
	issue_type: string;
	description: string;
	severity: 'error' | 'warning';
	scope: 'section' | 'document';
	check_source: 'mechanical' | 'llm';
}

export interface QualityReport {
	passed: boolean;
	issues: QualityIssue[];
	checked_at: string;
}

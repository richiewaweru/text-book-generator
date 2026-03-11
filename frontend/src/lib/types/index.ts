/** Mirrors backend Pydantic schemas for type safety. */

export type Depth = 'survey' | 'standard' | 'deep';
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
	provider?: string;
}

export interface GenerationResponse {
	textbook_id: string;
	output_path: string;
	quality_report: QualityReport | null;
	generation_time_seconds: number;
}

export interface GenerationProgress {
	current_node: string;
	completed_nodes: string[];
	total_nodes: number;
}

export interface GenerationStatus {
	id: string;
	status: 'pending' | 'running' | 'completed' | 'failed';
	progress: GenerationProgress | null;
	result: GenerationResponse | null;
	error: string | null;
}

export interface QualityIssue {
	section_id: string;
	issue_type: string;
	description: string;
	severity: 'error' | 'warning';
}

export interface QualityReport {
	passed: boolean;
	issues: QualityIssue[];
	checked_at: string;
}

/** Mirrors backend Pydantic schemas for type safety. */

export type Depth = 'survey' | 'standard' | 'deep';
export type NotationLanguage = 'plain' | 'math_notation' | 'python' | 'pseudocode';

export interface LearnerProfile {
	subject: string;
	age: number;
	context: string;
	depth: Depth;
	language: NotationLanguage;
}

export interface GenerationRequest extends LearnerProfile {
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

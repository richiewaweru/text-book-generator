export interface V3InputForm {
	// Step 1
	grade_level: string;
	subject: string;
	duration_minutes: number;

	// Step 2
	topic: string;
	subtopics: string[];
	prior_knowledge: string;

	// Step 3
	lesson_mode: 'first_exposure' | 'consolidation' | 'repair' | 'retrieval' | 'transfer' | 'other';
	lesson_mode_other: string;
	intended_outcome: 'understand' | 'practise' | 'review' | 'assess' | 'other';
	intended_outcome_other: string;

	// Step 4
	learner_level: 'below_grade' | 'on_grade' | 'above_grade' | 'mixed';
	reading_level: 'below_grade' | 'on_grade' | 'above_grade' | 'mixed';
	language_support: 'none' | 'some_ell' | 'many_ell';
	prior_knowledge_level: 'new_topic' | 'some_background' | 'reviewing';
	support_needs: string[];
	learning_preferences: ('visual' | 'step_by_step' | 'discussion' | 'hands_on' | 'challenge')[];

	// Step 5
	free_text: string;
}

export interface V3SignalSummary {
	topic: string;
	subtopic: string | null;
	prior_knowledge: string[];
	learner_needs: string[];
	teacher_goal: string;
	inferred_resource_type: string;
	confidence: 'low' | 'medium' | 'high';
	missing_signals: string[];
}

export interface V3ClarificationQuestion {
	question: string;
	reason: string;
	optional: boolean;
}

export interface V3ClarificationAnswer {
	question: string;
	answer: string;
}

export interface V3AppliedLens {
	id: string;
	label: string;
	reason: string;
	effects: string[];
}

export interface V3SectionPlanItem {
	id: string;
	title: string;
	order: number;
	learning_intent: string;
	components: V3ComponentPlan[];
	visual_required: boolean;
}

export interface V3ComponentPlan {
	component_id: string;
	teacher_label: string;
	content_intent: string;
}

export interface V3QuestionPlan {
	id: string;
	difficulty: 'warm' | 'medium' | 'cold' | 'transfer';
	expected_answer: string;
	diagram_required: boolean;
	attaches_to_section_id: string;
	prompt?: string;
}

export interface V3AnchorExample {
	label: string;
	facts: Record<string, string>;
	correct_result: string | null;
	reuse_scope: string;
}

export interface BlueprintPreviewDTO {
	blueprint_id: string;
	resource_type: string;
	title: string;
	template_id: string;
	lenses: V3AppliedLens[];
	anchor: V3AnchorExample | null;
	section_plan: V3SectionPlanItem[];
	question_plan: V3QuestionPlan[];
	register_summary: string;
	support_summary: string[];
}

export interface V3GenerationHistoryItem {
	id: string;
	subject: string;
	title: string;
	status: string;
	booklet_status: string;
	section_count: number;
	document_section_count: number;
	template_id: string;
	created_at: string | null;
	completed_at: string | null;
}

export interface V3GenerationDetail {
	id: string;
	subject: string;
	title: string;
	status: string;
	booklet_status: string;
	template_id: string;
	section_count: number;
	document_section_count: number;
	report_json: Record<string, unknown>;
	created_at: string | null;
	completed_at: string | null;
}

export type ComponentStatus = 'pending' | 'generating' | 'ready' | 'patched' | 'failed';

export interface CanvasComponent {
	id: string;
	teacher_label: string;
	status: ComponentStatus;
	data: Record<string, unknown> | null;
}

export interface CanvasVisual {
	id: string;
	status: ComponentStatus;
	image_url: string | null;
	frame_index: number | null;
}

export interface CanvasSection {
	id: string;
	title: string;
	teacher_labels: string;
	order: number;
	components: CanvasComponent[];
	visual: CanvasVisual | null;
	questions: Array<{
		id: string;
		difficulty: string;
		status: ComponentStatus;
		data: Record<string, unknown> | null;
	}>;
	/** Merged Lectio section fields (section_field → payload) for template render */
	mergedFields: Record<string, unknown>;
}

export type BookletStatus =
	| 'streaming_preview'
	| 'draft_ready'
	| 'draft_with_warnings'
	| 'draft_needs_review'
	| 'final_ready'
	| 'final_with_warnings'
	| 'failed_unusable';

export type SectionAssemblyStatus = 'complete' | 'incomplete' | 'failed';

export interface SectionAssemblyDiagnostic {
	section_id: string;
	status: SectionAssemblyStatus;
	renderable: boolean;
	missing_components: string[];
	missing_visuals: string[];
	warnings: string[];
}

export interface V3DraftPack {
	generation_id: string;
	blueprint_id: string;
	template_id: string;
	subject: string;
	status: BookletStatus;
	sections: Record<string, unknown>[];
	answer_key?: Record<string, unknown> | null;
	warnings: string[];
	section_diagnostics: SectionAssemblyDiagnostic[];
	booklet_issues: Array<Record<string, unknown>>;
}

export type V3Stage =
	| 'input'
	| 'confirming'
	| 'clarifying'
	| 'planning'
	| 'reviewing'
	| 'generating'
	| 'finalising'
	| 'complete';

export interface V3InputForm {
	year_group: string;
	subject: string;
	duration_minutes: number;
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

export type V3Stage =
	| 'input'
	| 'confirming'
	| 'clarifying'
	| 'planning'
	| 'reviewing'
	| 'generating'
	| 'finalising'
	| 'complete';

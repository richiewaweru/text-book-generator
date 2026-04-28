import type { TeacherBrief } from './brief';

export type StudioState = 'idle' | 'planning' | 'reviewing' | 'generating';
export type GenerationMode = 'draft' | 'balanced' | 'strict';
export type Tone = 'supportive' | 'neutral' | 'rigorous';
export type ReadingLevel = 'simple' | 'standard' | 'advanced';
export type ExplanationStyle = 'concrete-first' | 'concept-first' | 'balanced';
export type ExampleStyle = 'everyday' | 'academic' | 'exam';
export type Brevity = 'tight' | 'balanced' | 'expanded';
export type ScaffoldLevel = 'high' | 'medium' | 'low';
export type SectionRole =
	| 'intro'
	| 'explain'
	| 'practice'
	| 'summary'
	| 'process'
	| 'compare'
	| 'timeline'
	| 'visual'
	| 'discover';
export type VisualIntent =
	| 'explain_structure'
	| 'show_realism'
	| 'demonstrate_process'
	| 'compare_variants';
export type VisualMode = 'image' | 'svg';
export type PlanningStatus = 'draft' | 'reviewed' | 'committed';

export interface TemplateAlternative {
	template_id: string;
	template_name: string;
	fit_score: number;
	why_not_chosen: string;
}

export interface TemplateDecision {
	chosen_id: string;
	chosen_name: string;
	rationale: string;
	fit_score: number;
	alternatives: TemplateAlternative[];
}

export interface GenerationDirectives {
	tone_profile: Tone;
	reading_level: ReadingLevel;
	explanation_style: ExplanationStyle;
	example_style: ExampleStyle;
	scaffold_level: ScaffoldLevel;
	brevity: Brevity;
}

export interface VisualPolicy {
	required: boolean;
	intent: VisualIntent | null;
	mode: VisualMode | null;
	goal: string | null;
	style_notes: string | null;
}

export interface SectionGenerationNotes {
	tone_override: string | null;
	brevity_override: Brevity | null;
	explanation_override: string | null;
}

export interface PlanningBlockVisualPlacement {
	block: 'hook' | 'explanation' | 'practice' | 'worked_example';
	slot_type: 'diagram' | 'diagram_series' | 'diagram_compare';
	sizing?: 'full' | 'compact';
	hint?: string;
	problem_indices?: number[] | null;
}

export interface PlanningSectionPlan {
	id: string;
	order: number;
	role: SectionRole;
	title: string;
	objective: string | null;
	focus_note: string | null;
	selected_components: string[];
	visual_policy: VisualPolicy | null;
	generation_notes: SectionGenerationNotes | null;
	rationale: string;
	terms_to_define?: string[];
	terms_assumed?: string[];
	practice_target?: string | null;
	visual_placements?: PlanningBlockVisualPlacement[];
}

export interface PlanningGenerationSpec {
	id: string;
	template_id: string;
	preset_id: string;
	mode: GenerationMode;
	template_decision: TemplateDecision;
	lesson_rationale: string;
	directives: GenerationDirectives;
	committed_budgets: Record<string, number>;
	sections: PlanningSectionPlan[];
	warning: string | null;
	source_brief_id: string;
	source_brief: TeacherBrief;
	status: PlanningStatus;
}

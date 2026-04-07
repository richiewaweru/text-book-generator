export type Difficulty = 'warm' | 'medium' | 'cold' | 'extension';
export type GradeBand = 'primary' | 'secondary' | 'advanced';
export type HintLevel = 1 | 2 | 3;
export type BehaviourMode = 'static' | 'step-reveal' | 'accordion' | 'hint-toggle' | 'plain-formal-toggle' | 'zoom' | 'sticky' | 'drawer' | 'inline-strip' | 'progressive-hints' | 'compare' | 'flat-list' | 'timeline-scrubber';
export interface LevelPill {
    label: string;
    variant: 'all' | 'warm' | 'medium' | 'cold';
}
export interface SectionHeaderContent {
    title: string;
    subtitle?: string;
    subject: string;
    section_number?: string;
    grade_band: GradeBand;
    objectives?: string[];
    level_pills?: LevelPill[];
}
export type HookType = 'prose' | 'quote' | 'question' | 'data-point';
export interface HookImage {
    url: string;
    alt: string;
}
export interface HookHeroContent {
    headline: string;
    body: string;
    anchor: string;
    type?: HookType;
    image?: HookImage;
    svg_content?: string;
    quote_attribution?: string;
    question_options?: string[];
    data_point?: {
        value: string;
        label: string;
        source?: string;
    };
}
export interface ExplanationCallout {
    type: 'remember' | 'insight' | 'sidenote' | 'warning' | 'exam-tip';
    text: string;
}
export interface ExplanationContent {
    body: string;
    emphasis: string[];
    callouts?: ExplanationCallout[];
}
export interface PrerequisiteItem {
    concept: string;
    refresher?: string;
}
export interface PrerequisiteContent {
    label?: string;
    items: PrerequisiteItem[];
}
export interface WhatNextContent {
    body: string;
    next: string;
    preview?: string;
    prerequisites?: string[];
}
export interface InterviewContent {
    prompt: string;
    audience: string;
    follow_up?: string;
}
export type CalloutVariant = 'info' | 'tip' | 'warning' | 'exam-tip' | 'remember';
export interface CalloutBlockContent {
    variant: CalloutVariant;
    heading?: string;
    body: string;
}
export interface SummaryItem {
    text: string;
}
export interface SummaryBlockContent {
    heading?: string;
    items: SummaryItem[];
    closing?: string;
}
export interface SectionDividerContent {
    label: string;
}
export interface DefinitionContent {
    term: string;
    formal: string;
    plain: string;
    etymology?: string;
    notation?: string;
    related_terms?: string[];
    symbol?: string;
    examples?: string[];
}
export interface DefinitionFamilyContent {
    family_title: string;
    family_intro?: string;
    definitions: DefinitionContent[];
}
export interface GlossaryTerm {
    term: string;
    definition: string;
    used_in?: string;
    pronunciation?: string;
    related?: string[];
}
export interface GlossaryContent {
    terms: GlossaryTerm[];
}
export interface GlossaryInlineProps {
    term: string;
    definition: string;
}
export interface InsightCell {
    label: string;
    value: string;
    note?: string;
    highlight?: boolean;
}
export interface InsightStripContent {
    cells: InsightCell[];
}
export interface KeyFactContent {
    fact: string;
    context?: string;
    source?: string;
}
export interface ComparisonColumn {
    id: string;
    title: string;
    summary: string;
    badge?: string;
    detail?: string;
    highlight?: boolean;
}
export interface ComparisonRow {
    criterion: string;
    values: string[];
    takeaway?: string;
}
export interface ComparisonGridContent {
    title: string;
    intro?: string;
    columns: ComparisonColumn[];
    rows: ComparisonRow[];
    apply_prompt?: string;
}
export interface WorkedStep {
    label: string;
    content: string;
    note?: string;
    formula?: string;
    diagram_ref?: string;
}
export interface WorkedExampleContent {
    title: string;
    setup: string;
    steps: WorkedStep[];
    conclusion: string;
    method_label?: string;
    alternative?: WorkedExampleContent;
    answer?: string;
    alternatives?: string[];
}
export interface ProcessStepItem {
    number: number;
    action: string;
    detail: string;
    input?: string;
    output?: string;
    warning?: string;
}
export interface ProcessContent {
    title: string;
    intro?: string;
    steps: ProcessStepItem[];
    checklist_mode?: boolean;
}
export interface PracticeHint {
    level: HintLevel;
    text: string;
}
export interface PracticeSolution {
    approach: string;
    answer: string;
    worked?: string;
}
export interface PracticeProblem {
    difficulty: Difficulty;
    problem_type?: 'structured' | 'open';
    question: string;
    hints: PracticeHint[];
    solution?: PracticeSolution;
    writein_lines?: number;
    self_assess?: boolean;
    context?: string;
}
export interface PracticeContent {
    problems: PracticeProblem[];
    hints_visible_default?: boolean;
    solutions_available?: boolean;
    label?: string;
}
export interface QuizOption {
    text: string;
    correct: boolean;
    explanation: string;
}
export interface QuizContent {
    question: string;
    quiz_type?: 'multiple-choice' | 'true-false';
    options: QuizOption[];
    feedback_correct: string;
    feedback_incorrect: string;
    show_explanations?: boolean;
}
export type ReflectionType = 'open' | 'pair-share' | 'sentence-stem' | 'timed' | 'connect' | 'predict' | 'transfer';
export interface ReflectionContent {
    prompt: string;
    type: ReflectionType;
    space?: number;
    sentence_stem?: string;
    time_minutes?: number;
    pair_instruction?: string;
}
export interface StudentTextboxContent {
    prompt: string;
    lines?: number;
    label?: string;
}
export interface ShortAnswerContent {
    question: string;
    marks?: number;
    lines?: number;
    mark_scheme?: string;
}
export interface FillInBlankSegment {
    text: string;
    is_blank: boolean;
    answer?: string;
}
export interface FillInBlankContent {
    instruction?: string;
    segments: FillInBlankSegment[];
    word_bank?: string[];
}
export interface PitfallContent {
    misconception: string;
    correction: string;
    example?: string;
    severity?: 'minor' | 'major';
    examples?: string[];
    why?: string;
}
export interface DiagramCallout {
    id: string;
    x: number;
    y: number;
    label: string;
    explanation: string;
}
export interface DiagramContent {
    svg_content?: string;
    image_url?: string;
    caption: string;
    zoom_label?: string;
    alt_text: string;
    callouts?: DiagramCallout[];
    figure_number?: number;
}
export interface DiagramCompareContent {
    before_svg: string;
    after_svg: string;
    before_label: string;
    after_label: string;
    before_details?: string[];
    after_details?: string[];
    caption: string;
    alt_text: string;
}
export interface DiagramSeriesStep {
    step_label: string;
    caption: string;
    svg_content?: string;
    image_url?: string;
}
export interface DiagramSeriesContent {
    title: string;
    diagrams: DiagramSeriesStep[];
}
export interface TimelineEvent {
    id: string;
    era?: string;
    year: string;
    title: string;
    summary: string;
    impact?: string;
    tags?: string[];
}
export interface TimelineContent {
    title: string;
    intro?: string;
    events: TimelineEvent[];
    closing_takeaway?: string;
}
export type SimulationType = 'graph_slider' | 'probability_tree' | 'equation_reveal' | 'geometry_explorer' | 'molecule_viewer' | 'timeline_scrubber';
export interface InteractionSpec {
    type: SimulationType;
    goal: string;
    anchor_content: Record<string, unknown>;
    context: {
        learner_level: string;
        template_id: string;
        color_mode: 'light' | 'dark';
        accent_color: string;
        surface_color: string;
        font_mono: string;
    };
    dimensions: {
        width: string;
        height: number;
        resizable: boolean;
    };
    print_translation: 'static_midstate' | 'static_diagram' | 'hide';
}
export interface SimulationContent {
    spec: InteractionSpec;
    html_content?: string;
    fallback_diagram?: DiagramContent;
    explanation?: string;
}
export interface VideoEmbedContent {
    media_id: string;
    caption?: string;
    start_time?: number;
    end_time?: number;
    print_fallback: 'thumbnail' | 'qr-link' | 'hide';
}
export interface ImageBlockContent {
    media_id: string;
    caption?: string;
    alt_text: string;
    width?: 'full' | 'half' | 'third';
    alignment?: 'left' | 'center' | 'right';
}
export interface SectionContent {
    section_id: string;
    template_id: string;
    header: SectionHeaderContent;
    hook: HookHeroContent;
    explanation: ExplanationContent;
    practice: PracticeContent;
    what_next: WhatNextContent;
    prerequisites?: PrerequisiteContent;
    definition?: DefinitionContent;
    definition_family?: DefinitionFamilyContent;
    worked_example?: WorkedExampleContent;
    worked_examples?: WorkedExampleContent[];
    process?: ProcessContent;
    diagram?: DiagramContent;
    diagram_compare?: DiagramCompareContent;
    diagram_series?: DiagramSeriesContent;
    video_embed?: VideoEmbedContent;
    image_block?: ImageBlockContent;
    comparison_grid?: ComparisonGridContent;
    timeline?: TimelineContent;
    insight_strip?: InsightStripContent;
    pitfall?: PitfallContent;
    pitfalls?: PitfallContent[];
    quiz?: QuizContent;
    reflection?: ReflectionContent;
    glossary?: GlossaryContent;
    simulations?: SimulationContent[];
    simulation?: SimulationContent;
    interview?: InterviewContent;
    callout?: CalloutBlockContent;
    summary?: SummaryBlockContent;
    student_textbox?: StudentTextboxContent;
    short_answer?: ShortAnswerContent;
    fill_in_blank?: FillInBlankContent;
    divider?: SectionDividerContent;
    key_fact?: KeyFactContent;
}

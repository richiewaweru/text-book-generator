import { getComponentFieldMap } from './registry';
const defaultGrade = 'secondary';
const factories = {
    'section-header': () => ({
        title: '',
        subject: '',
        grade_band: defaultGrade,
        objectives: []
    }),
    'hook-hero': () => ({
        headline: '',
        body: '',
        anchor: '',
        type: 'prose'
    }),
    'explanation-block': () => ({
        body: '',
        emphasis: []
    }),
    'prerequisite-strip': () => ({
        items: []
    }),
    'what-next-bridge': () => ({
        body: '',
        next: ''
    }),
    'interview-anchor': () => ({
        prompt: '',
        audience: ''
    }),
    'callout-block': () => ({
        variant: 'info',
        body: ''
    }),
    'summary-block': () => ({
        items: []
    }),
    'section-divider': () => ({
        label: ''
    }),
    'definition-card': () => ({
        term: '',
        formal: '',
        plain: ''
    }),
    'definition-family': () => ({
        family_title: '',
        definitions: []
    }),
    'glossary-rail': () => ({
        terms: []
    }),
    'insight-strip': () => ({
        cells: [
            { label: '', value: '' },
            { label: '', value: '' }
        ]
    }),
    'key-fact': () => ({
        fact: ''
    }),
    'comparison-grid': () => ({
        title: '',
        columns: [],
        rows: []
    }),
    'worked-example-card': () => ({
        title: '',
        setup: '',
        steps: [],
        conclusion: ''
    }),
    'process-steps': () => ({
        title: '',
        steps: []
    }),
    'practice-stack': () => ({
        problems: [
            {
                difficulty: 'warm',
                question: '',
                hints: []
            },
            {
                difficulty: 'medium',
                question: '',
                hints: []
            }
        ]
    }),
    'quiz-check': () => ({
        question: '',
        options: [
            { text: '', correct: false, explanation: '' },
            { text: '', correct: false, explanation: '' },
            { text: '', correct: true, explanation: '' }
        ],
        feedback_correct: '',
        feedback_incorrect: ''
    }),
    'reflection-prompt': () => ({
        prompt: '',
        type: 'open'
    }),
    'student-textbox': () => ({
        prompt: ''
    }),
    'short-answer': () => ({
        question: ''
    }),
    'fill-in-blank': () => ({
        segments: []
    }),
    'pitfall-alert': () => ({
        misconception: '',
        correction: ''
    }),
    'diagram-block': () => ({
        svg_content: '',
        caption: '',
        alt_text: ''
    }),
    'diagram-compare': () => ({
        before_svg: '',
        after_svg: '',
        before_label: '',
        after_label: '',
        caption: '',
        alt_text: ''
    }),
    'diagram-series': () => ({
        title: '',
        diagrams: []
    }),
    'video-embed': () => ({
        media_id: '',
        print_fallback: 'thumbnail'
    }),
    'image-block': () => ({
        media_id: '',
        alt_text: '',
        width: 'full',
        alignment: 'center'
    }),
    'timeline-block': () => ({
        title: '',
        events: []
    }),
    'simulation-block': () => ({
        spec: {
            type: 'graph_slider',
            goal: '',
            anchor_content: {},
            context: {
                learner_level: '',
                template_id: '',
                color_mode: 'light',
                accent_color: '',
                surface_color: '',
                font_mono: ''
            },
            dimensions: { width: '100%', height: 400, resizable: false },
            print_translation: 'static_midstate'
        }
    })
};
/**
 * Valid placeholder content for a component. Required fields use empty or minimal values.
 */
export function getEmptyContent(componentId) {
    const factory = factories[componentId];
    if (!factory) {
        throw new Error(`[Lectio] No empty content factory for component "${componentId}"`);
    }
    return factory();
}
/**
 * Richer demo content for palette previews. Extend per-component as needed.
 */
export function getPreviewContent(componentId) {
    return getEmptyContent(componentId);
}
/** Every component with a section field must have a factory (builder + document conversion). */
export function assertFactoriesCoverRegistry() {
    const map = getComponentFieldMap();
    for (const componentId of Object.keys(map)) {
        if (!factories[componentId]) {
            throw new Error(`[Lectio] Missing getEmptyContent factory for "${componentId}"`);
        }
    }
}

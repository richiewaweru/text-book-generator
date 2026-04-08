import { getComponentById, getComponentFieldMap } from './registry';
import { getEmptyContent } from './content-factories';
import { getSectionSimulations } from './section-content';
import { validateSection } from './validate';
/**
 * Field name → component registry id. Inverse of getComponentFieldMap().
 * Only keys that map to a block component appear.
 */
export function getFieldComponentMap() {
    const forward = getComponentFieldMap();
    const reverse = {};
    for (const [componentId, field] of Object.entries(forward)) {
        reverse[field] = componentId;
    }
    return reverse;
}
/** Canonical block order within a section (template lessonFlow removed; this is stable UI order). */
const BLOCK_FIELD_ORDER = [
    'header',
    'hook',
    'prerequisites',
    'divider',
    'explanation',
    'definition',
    'definition_family',
    'key_fact',
    'callout',
    'insight_strip',
    'comparison_grid',
    'diagram',
    'diagram_compare',
    'diagram_series',
    'video_embed',
    'image_block',
    'timeline',
    'worked_example',
    'worked_examples',
    'process',
    'simulations',
    'pitfall',
    'pitfalls',
    'practice',
    'quiz',
    'short_answer',
    'fill_in_blank',
    'student_textbox',
    'reflection',
    'interview',
    'glossary',
    'summary',
    'what_next'
];
function newId() {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
        return crypto.randomUUID();
    }
    return `id-${Math.random().toString(36).slice(2, 11)}-${Date.now()}`;
}
function deepClone(value) {
    return structuredClone(value);
}
function extractBlocksFromSection(section) {
    const fieldToComp = getFieldComponentMap();
    const out = [];
    for (const field of BLOCK_FIELD_ORDER) {
        if (field === 'worked_examples') {
            for (const w of section.worked_examples ?? []) {
                out.push({ componentId: 'worked-example-card', content: w });
            }
            continue;
        }
        if (field === 'pitfalls') {
            for (const p of section.pitfalls ?? []) {
                out.push({ componentId: 'pitfall-alert', content: p });
            }
            continue;
        }
        if (field === 'simulations') {
            for (const simulation of getSectionSimulations(section)) {
                out.push({ componentId: 'simulation-block', content: simulation });
            }
            continue;
        }
        const val = section[field];
        if (val === undefined || val === null)
            continue;
        const compId = fieldToComp[field];
        if (!compId)
            continue;
        out.push({ componentId: compId, content: val });
    }
    return out;
}
/**
 * Decompose SectionContent[] into a LessonDocument.
 * Preserves section_id as DocumentSection.id for stable round-trips.
 */
export function fromSectionContents(sections, metadata) {
    const blocks = {};
    const docSections = [];
    const now = new Date().toISOString();
    const source = metadata.source ?? (metadata.source_generation_id ? 'generated' : 'template');
    let sectionPosition = 0;
    for (const section of sections) {
        const extracted = extractBlocksFromSection(section);
        const block_ids = [];
        let blockPos = 0;
        for (const { componentId, content } of extracted) {
            const id = newId();
            block_ids.push(id);
            blocks[id] = {
                id,
                component_id: componentId,
                content: deepClone(content),
                position: blockPos++
            };
        }
        docSections.push({
            id: section.section_id,
            template_id: section.template_id || metadata.template_id || 'unknown',
            block_ids,
            title: section.header.title,
            position: sectionPosition++
        });
    }
    return {
        version: 1,
        id: newId(),
        title: metadata.title,
        subject: metadata.subject,
        preset_id: metadata.preset_id,
        source,
        source_generation_id: metadata.source_generation_id,
        grade_band: metadata.grade_band,
        sections: docSections,
        blocks,
        media: {},
        created_at: now,
        updated_at: now
    };
}
function emptySectionShell(docSection) {
    return {
        section_id: docSection.id,
        template_id: docSection.template_id,
        header: getEmptyContent('section-header'),
        hook: getEmptyContent('hook-hero'),
        explanation: getEmptyContent('explanation-block'),
        practice: getEmptyContent('practice-stack'),
        what_next: getEmptyContent('what-next-bridge')
    };
}
function applyBlockToSection(section, componentId, content) {
    const fieldMap = getComponentFieldMap();
    if (componentId === 'pitfall-alert') {
        const p = content;
        if (!section.pitfall) {
            section.pitfall = p;
        }
        else {
            if (!section.pitfalls)
                section.pitfalls = [];
            section.pitfalls.push(p);
        }
        return;
    }
    if (componentId === 'worked-example-card') {
        const w = content;
        if (!section.worked_example) {
            section.worked_example = w;
        }
        else {
            if (!section.worked_examples)
                section.worked_examples = [];
            section.worked_examples.push(w);
        }
        return;
    }
    if (componentId === 'simulation-block') {
        if (!section.simulations)
            section.simulations = [];
        section.simulations.push(deepClone(content));
        return;
    }
    const field = fieldMap[componentId];
    if (!field)
        return;
    section[field] = deepClone(content);
}
/**
 * Rebuild SectionContent[] from a LessonDocument (for rendering / validation).
 */
export function toSectionContents(document) {
    const ordered = [...document.sections].sort((a, b) => a.position - b.position);
    return ordered.map((docSection) => {
        const section = emptySectionShell(docSection);
        for (const blockId of docSection.block_ids) {
            const block = document.blocks[blockId];
            if (!block)
                continue;
            applyBlockToSection(section, block.component_id, block.content);
        }
        return section;
    });
}
/**
 * Structural + capacity validation. Structural problems set valid=false.
 */
export function validateDocument(document) {
    const errors = [];
    const warnings = [];
    if (document.version !== 1) {
        errors.push(`Unsupported document version: ${document.version} (expected 1).`);
    }
    for (const key of ['id', 'title', 'subject', 'preset_id', 'sections', 'blocks']) {
        if (document[key] === undefined) {
            errors.push(`Missing required field: ${key}`);
        }
    }
    if (!document.media) {
        errors.push('Missing required field: media');
    }
    for (const sec of document.sections) {
        for (const bid of sec.block_ids) {
            if (!document.blocks[bid]) {
                errors.push(`Section "${sec.id}" references missing block id "${bid}".`);
            }
        }
    }
    for (const block of Object.values(document.blocks)) {
        if (!getComponentById(block.component_id)) {
            errors.push(`Unknown component_id on block "${block.id}": "${block.component_id}".`);
        }
    }
    if (errors.length > 0) {
        return { valid: false, errors, warnings };
    }
    const sections = toSectionContents(document);
    sections.forEach((sec) => {
        const w = validateSection(sec);
        for (const msg of w) {
            warnings.push(`[${sec.section_id}] ${msg}`);
        }
    });
    return { valid: true, errors: [], warnings };
}

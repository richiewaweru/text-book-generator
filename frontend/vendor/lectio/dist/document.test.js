import { describe, expect, it } from 'vitest';
import { calculusSection } from './dummy-content';
import { fromSectionContents, toSectionContents, validateDocument } from './document';
describe('LessonDocument conversion', () => {
    it('round-trips a rich section through fromSectionContents and toSectionContents', () => {
        const doc = fromSectionContents([calculusSection], {
            title: calculusSection.header.title,
            subject: calculusSection.header.subject,
            preset_id: 'blue-classroom',
            source: 'template',
            grade_band: calculusSection.header.grade_band
        });
        expect(doc.version).toBe(1);
        expect(doc.sections).toHaveLength(1);
        expect(doc.sections[0].id).toBe(calculusSection.section_id);
        const back = toSectionContents(doc)[0];
        expect(back).toEqual(calculusSection);
    });
    it('validateDocument passes for a converted document', () => {
        const doc = fromSectionContents([calculusSection], {
            title: 'T',
            subject: 'Mathematics',
            preset_id: 'blue-classroom',
            source: 'generated',
            source_generation_id: 'gen-1'
        });
        const result = validateDocument(doc);
        expect(result.valid).toBe(true);
        expect(result.errors).toHaveLength(0);
    });
    it('validateDocument reports structural errors', () => {
        const doc = fromSectionContents([calculusSection], {
            title: 'T',
            subject: 'Mathematics',
            preset_id: 'blue-classroom'
        });
        doc.sections[0].block_ids.push('missing-block');
        const result = validateDocument(doc);
        expect(result.valid).toBe(false);
        expect(result.errors.some((e) => e.includes('missing-block'))).toBe(true);
    });
});

import { describe, expect, it } from 'vitest';
import { assertFactoriesCoverRegistry, getEmptyContent } from './content-factories';
import { getComponentFieldMap } from './registry';
import { validateSection } from './validate';
describe('content-factories', () => {
    it('covers every registry component that has a section field', () => {
        expect(() => assertFactoriesCoverRegistry()).not.toThrow();
    });
    it('getEmptyContent produces section slices that validate without hard errors for core fields', () => {
        const fieldMap = getComponentFieldMap();
        const header = getEmptyContent('section-header');
        const hook = getEmptyContent('hook-hero');
        const explanation = getEmptyContent('explanation-block');
        const practice = getEmptyContent('practice-stack');
        const whatNext = getEmptyContent('what-next-bridge');
        const section = {
            section_id: 's1',
            template_id: 't1',
            header,
            hook,
            explanation,
            practice,
            what_next: whatNext
        };
        const warnings = validateSection(section);
        expect(Array.isArray(warnings)).toBe(true);
    });
    it('throws for unknown component id', () => {
        expect(() => getEmptyContent('not-a-real-component')).toThrow();
    });
    it('has a factory entry for each mapped component id', () => {
        const map = getComponentFieldMap();
        for (const id of Object.keys(map)) {
            expect(() => getEmptyContent(id)).not.toThrow();
        }
    });
    it('seeds diagram compare content with both svg and image fields for builder parity', () => {
        expect(getEmptyContent('diagram-compare')).toMatchObject({
            before_svg: '',
            after_svg: '',
            before_image_url: '',
            after_image_url: ''
        });
    });
});

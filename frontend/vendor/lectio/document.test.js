import { describe, expect, it } from 'vitest';
import { calculusSection, physicsSection } from './dummy-content';
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
    it('preserves repeated simulation blocks through document round-trips', () => {
        const secondSimulation = {
            ...physicsSection.simulations[0],
            explanation: 'A second interaction that extends the same concept.',
            spec: {
                ...physicsSection.simulations[0].spec,
                goal: 'Compare how a second interaction reinforces Newtons Second Law.'
            }
        };
        const section = {
            ...physicsSection,
            section_id: 'phys-02-multi',
            simulations: [physicsSection.simulations[0], secondSimulation]
        };
        const doc = fromSectionContents([section], {
            title: section.header.title,
            subject: section.header.subject,
            preset_id: 'blue-classroom'
        });
        const simulationBlocks = Object.values(doc.blocks).filter((block) => block.component_id === 'simulation-block');
        expect(simulationBlocks).toHaveLength(2);
        const back = toSectionContents(doc)[0];
        expect(back.simulations).toEqual(section.simulations);
    });
    it('reads legacy singular simulation content and rebuilds the plural shape', () => {
        const legacySection = {
            ...physicsSection,
            section_id: 'phys-02-legacy',
            simulations: undefined,
            simulation: physicsSection.simulations[0]
        };
        const doc = fromSectionContents([legacySection], {
            title: legacySection.header.title,
            subject: legacySection.header.subject,
            preset_id: 'blue-classroom'
        });
        const back = toSectionContents(doc)[0];
        expect(back.simulations).toEqual([physicsSection.simulations[0]]);
        expect(back.simulation).toBeUndefined();
    });
});

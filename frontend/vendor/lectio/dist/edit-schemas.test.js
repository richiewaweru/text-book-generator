import { describe, expect, it } from 'vitest';
import { getEditSchema } from './edit-schemas';
import { getComponentFieldMap } from './registry';
describe('edit-schemas', () => {
    it('returns a schema for every component with a section field', () => {
        const map = getComponentFieldMap();
        for (const componentId of Object.keys(map)) {
            const schema = getEditSchema(componentId);
            expect(schema, componentId).not.toBeNull();
            expect(schema.component_id).toBe(componentId);
            expect(schema.fields.length).toBeGreaterThan(0);
        }
    });
    it('returns null for glossary-inline (no block field)', () => {
        expect(getEditSchema('glossary-inline')).toBeNull();
    });
});

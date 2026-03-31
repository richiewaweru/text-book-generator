import type { BehaviourMode, SectionContent } from './types';
export interface ComponentMeta {
    id: string;
    /** Short label for the builder palette */
    teacherLabel: string;
    /** One-sentence description for teachers */
    teacherDescription: string;
    name: string;
    purpose: string;
    cognitiveJob: string;
    subjects: string[];
    behaviourModes: BehaviourMode[];
    shadcnPrimitive: string;
    capacity: Record<string, number | string>;
    printFallback: string;
    status: 'stable' | 'beta' | 'planned';
    group: 1 | 2 | 3 | 4 | 5 | 6 | 7;
    /**
     * The field in SectionContent this component reads from.
     *
     * null means the component has no dedicated SectionContent block field.
     * Example: GlossaryInline is used inline in prose — it is not a block.
     *
     * This is the single source of truth for the component-to-field mapping.
     * template-validation.ts and scripts/export-contracts.ts both derive
     * their maps from this field via getComponentFieldMap().
     * Never hardcode this mapping anywhere else.
     */
    sectionField: keyof SectionContent | null;
}
export declare const componentRegistry: Record<string, ComponentMeta>;
export declare function getStableComponents(): ComponentMeta[];
export declare function getComponentsByGroup(group: number): ComponentMeta[];
export declare function getComponentsForSubject(subject: string): ComponentMeta[];
export declare function getComponentById(componentId: string): ComponentMeta | undefined;
/**
 * Derive the component-id → SectionContent-field map from the registry.
 *
 * This is the authoritative mapping used by:
 *   - template-validation.ts  (preview field presence checks)
 *   - scripts/export-contracts.ts  (pipeline contract export)
 *
 * Components with sectionField: null are excluded — they have no
 * corresponding block field in SectionContent.
 *
 * When you register a new component with a sectionField, it appears
 * in this map automatically. No other file needs to change.
 */
export declare function getComponentFieldMap(): Record<string, keyof SectionContent>;

import { validateTemplateDefinition } from './template-validation';
import { classificationContract } from './templates/classification/config';
import ClassificationLayout from './templates/classification/layout.svelte';
import { classificationPresets } from './templates/classification/presets';
import { classificationPreview } from './templates/classification/preview';
import { compareAndApplyContract } from './templates/compare-and-apply/config';
import CompareAndApplyLayout from './templates/compare-and-apply/layout.svelte';
import { compareAndApplyPresets } from './templates/compare-and-apply/presets';
import { compareAndApplyPreview } from './templates/compare-and-apply/preview';
import { conceptCompactContract } from './templates/concept-compact/config';
import ConceptCompactLayout from './templates/concept-compact/layout.svelte';
import { conceptCompactPresets } from './templates/concept-compact/presets';
import { conceptCompactPreview } from './templates/concept-compact/preview';
import { diagramLedContract } from './templates/diagram-led/config';
import DiagramLedLayout from './templates/diagram-led/layout.svelte';
import { diagramLedPresets } from './templates/diagram-led/presets';
import { diagramLedPreview } from './templates/diagram-led/preview';
import { formalTrackContract } from './templates/formal-track/config';
import FormalTrackLayout from './templates/formal-track/layout.svelte';
import { formalTrackPresets } from './templates/formal-track/presets';
import { formalTrackPreview } from './templates/formal-track/preview';
import { guidedConceptPathContract } from './templates/guided-concept-path/config';
import GuidedConceptPathLayout from './templates/guided-concept-path/layout.svelte';
import { guidedConceptPathPresets } from './templates/guided-concept-path/presets';
import { guidedConceptPathPreview } from './templates/guided-concept-path/preview';
import { guidedDiscoveryContract } from './templates/guided-discovery/config';
import GuidedDiscoveryLayout from './templates/guided-discovery/layout.svelte';
import { guidedDiscoveryPresets } from './templates/guided-discovery/presets';
import { guidedDiscoveryPreview } from './templates/guided-discovery/preview';
import { interactiveLabContract } from './templates/interactive-lab/config';
import InteractiveLabLayout from './templates/interactive-lab/layout.svelte';
import { interactiveLabPresets } from './templates/interactive-lab/presets';
import { interactiveLabPreview } from './templates/interactive-lab/preview';
import { lowLoadContract } from './templates/low-load/config';
import LowLoadLayout from './templates/low-load/layout.svelte';
import { lowLoadPresets } from './templates/low-load/presets';
import { lowLoadPreview } from './templates/low-load/preview';
import { procedureContract } from './templates/procedure/config';
import ProcedureLayout from './templates/procedure/layout.svelte';
import { procedurePresets } from './templates/procedure/presets';
import { procedurePreview } from './templates/procedure/preview';
import { timelineContract } from './templates/timeline/config';
import TimelineLayout from './templates/timeline/layout.svelte';
import { timelinePresets } from './templates/timeline/presets';
import { timelinePreview } from './templates/timeline/preview';
import { openCanvasContract } from './templates/open-canvas/config';
import OpenCanvasLayout from './templates/open-canvas/layout.svelte';
import { openCanvasPresets } from './templates/open-canvas/presets';
import { openCanvasPreview } from './templates/open-canvas/preview';
import { visualLedContract } from './templates/visual-led/config';
import VisualLedLayout from './templates/visual-led/layout.svelte';
import { visualLedPresets } from './templates/visual-led/presets';
import { visualLedPreview } from './templates/visual-led/preview';
export const templateRegistry = [
    {
        contract: guidedConceptPathContract,
        preview: guidedConceptPathPreview,
        presets: guidedConceptPathPresets,
        render: GuidedConceptPathLayout,
        readmePath: 'src/lib/templates/guided-concept-path/README.md'
    },
    {
        contract: visualLedContract,
        preview: visualLedPreview,
        presets: visualLedPresets,
        render: VisualLedLayout,
        readmePath: 'src/lib/templates/visual-led/README.md'
    },
    {
        contract: compareAndApplyContract,
        preview: compareAndApplyPreview,
        presets: compareAndApplyPresets,
        render: CompareAndApplyLayout,
        readmePath: 'src/lib/templates/compare-and-apply/README.md'
    },
    {
        contract: lowLoadContract,
        preview: lowLoadPreview,
        presets: lowLoadPresets,
        render: LowLoadLayout,
        readmePath: 'src/lib/templates/low-load/README.md'
    },
    {
        contract: conceptCompactContract,
        preview: conceptCompactPreview,
        presets: conceptCompactPresets,
        render: ConceptCompactLayout,
        readmePath: 'src/lib/templates/concept-compact/README.md'
    },
    {
        contract: formalTrackContract,
        preview: formalTrackPreview,
        presets: formalTrackPresets,
        render: FormalTrackLayout,
        readmePath: 'src/lib/templates/formal-track/README.md'
    },
    {
        contract: diagramLedContract,
        preview: diagramLedPreview,
        presets: diagramLedPresets,
        render: DiagramLedLayout,
        readmePath: 'src/lib/templates/diagram-led/README.md'
    },
    {
        contract: classificationContract,
        preview: classificationPreview,
        presets: classificationPresets,
        render: ClassificationLayout,
        readmePath: 'src/lib/templates/classification/README.md'
    },
    {
        contract: timelineContract,
        preview: timelinePreview,
        presets: timelinePresets,
        render: TimelineLayout,
        readmePath: 'src/lib/templates/timeline/README.md'
    },
    {
        contract: procedureContract,
        preview: procedurePreview,
        presets: procedurePresets,
        render: ProcedureLayout,
        readmePath: 'src/lib/templates/procedure/README.md'
    },
    {
        contract: interactiveLabContract,
        preview: interactiveLabPreview,
        presets: interactiveLabPresets,
        render: InteractiveLabLayout,
        readmePath: 'src/lib/templates/interactive-lab/README.md'
    },
    {
        contract: guidedDiscoveryContract,
        preview: guidedDiscoveryPreview,
        presets: guidedDiscoveryPresets,
        render: GuidedDiscoveryLayout,
        readmePath: 'src/lib/templates/guided-discovery/README.md'
    },
    {
        contract: openCanvasContract,
        preview: openCanvasPreview,
        presets: openCanvasPresets,
        render: OpenCanvasLayout,
        readmePath: 'src/lib/templates/open-canvas/README.md'
    }
];
export const templateRegistryMap = Object.fromEntries(templateRegistry.map((definition) => [definition.contract.id, definition]));
export function getTemplateById(templateId) {
    return templateRegistryMap[templateId];
}
export function filterTemplates(filters) {
    return templateRegistry.filter((definition) => {
        const { contract } = definition;
        if (filters.family && contract.family !== filters.family) {
            return false;
        }
        if (filters.intent && contract.intent !== filters.intent) {
            return false;
        }
        if (filters.learnerFit && !contract.learnerFit.includes(filters.learnerFit)) {
            return false;
        }
        if (filters.subject &&
            !contract.subjects.some((subject) => subject.toLowerCase() === filters.subject?.toLowerCase())) {
            return false;
        }
        if (filters.interactionLevel && contract.interactionLevel !== filters.interactionLevel) {
            return false;
        }
        return true;
    });
}
export function getTemplateFamilies() {
    return Array.from(new Set(templateRegistry.map((definition) => definition.contract.family)));
}
export function validateAllTemplates() {
    return templateRegistry.map((definition) => ({
        id: definition.contract.id,
        ...validateTemplateDefinition(definition)
    }));
}

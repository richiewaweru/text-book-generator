// ── Components ──────────────────────────────────────
export { SectionHeader, HookHero, ExplanationBlock, PrerequisiteStrip, WhatNextBridge, InterviewAnchor, CalloutBlock, SummaryBlock, SectionDivider, DefinitionCard, DefinitionFamily, GlossaryRail, GlossaryInline, InsightStrip, KeyFact, ComparisonGrid, WorkedExampleCard, ProcessSteps, PracticeStack, QuizCheck, ReflectionPrompt, StudentTextbox, ShortAnswerQuestion, FillInTheBlank, PitfallAlert, DiagramBlock, DiagramCompare, DiagramSeries, VideoEmbed, ImageBlock, TimelineBlock, SimulationBlock } from './components/lectio';
// ── Registry ────────────────────────────────────────
export { componentRegistry, getStableComponents, getComponentsByGroup, getComponentsForSubject, getComponentById, getComponentFieldMap } from './registry';
// ── Validation ──────────────────────────────────────
export { validateSection, warnIfInvalid } from './validate';
export { fromSectionContents, toSectionContents, validateDocument, getFieldComponentMap } from './document';
export { getEmptyContent, getPreviewContent, assertFactoriesCoverRegistry } from './content-factories';
export { getEditSchema } from './edit-schemas';
// ── Template system ─────────────────────────────────
export { templateRegistry, templateRegistryMap, getTemplateById, filterTemplates, getTemplateFamilies, validateAllTemplates } from './template-registry';
export { default as LectioThemeSurface } from './templates/LectioThemeSurface.svelte';
export { default as ResolvedTemplatePreviewSurface } from './templates/ResolvedTemplatePreviewSurface.svelte';
export { default as TemplateRuntimeSurface } from './templates/TemplateRuntimeSurface.svelte';
export { default as TemplatePreviewSurface } from './templates/TemplatePreviewSurface.svelte';
export { validateTemplateDefinition, validateTemplateContract, validateTemplatePreview } from './template-validation';
// ── Presets ─────────────────────────────────────────
export { basePresets, basePresetMap } from './presets/base-presets';
// ── Utility ─────────────────────────────────────────
export { cn } from './utils';
// ── Markdown utilities ───────────────────────────────
export { renderInlineMarkdown, renderBlockMarkdown, looksLikeLatex } from './markdown';
// ── Print utilities ──────────────────────────────────
export { default as RuledLines } from './print/RuledLines.svelte';
export { default as Checkboxes } from './print/Checkboxes.svelte';
export { default as ExpandedSteps } from './print/ExpandedSteps.svelte';
export { default as SideBySide } from './print/SideBySide.svelte';
export { default as VerticalList } from './print/VerticalList.svelte';
export { default as AnswerMarker } from './print/AnswerMarker.svelte';
export { providePrintMode, usePrintMode } from './utils/printContext';

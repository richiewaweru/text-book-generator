import { describe, it, expect } from 'vitest';
import { componentRegistry } from './registry';
/**
 * Registry compliance test for print fallbacks.
 *
 * Verifies that the printFallback strings in the registry match
 * the known expected values for each of the 15 interactive components
 * that have print-specific implementations.
 *
 * This test exists to catch accidental drift between the registry
 * description and the actual implemented behaviour.
 */
describe('Print Fallback Registry Compliance', () => {
    it('every component in the registry has a non-empty printFallback', () => {
        for (const [key, meta] of Object.entries(componentRegistry)) {
            expect(meta.printFallback, `${key} (id: ${meta.id}) is missing a printFallback string`).toBeTruthy();
        }
    });
    it('high-priority interactive components have correct printFallback strings', () => {
        const expected = {
            'quiz-check': 'Question and options shown, correct answer marked',
            'practice-stack': 'All visible, write-in lines rendered',
            'worked-example-card': 'All steps expanded',
            'simulation-block': 'Static diagram at midstate',
            'fill-in-blank': 'Passage with underlined blanks, word bank box below',
            'diagram-compare': 'Both diagrams shown side by side',
            'timeline-block': 'Vertical event list'
        };
        for (const [id, expectedFallback] of Object.entries(expected)) {
            const meta = Object.values(componentRegistry).find((c) => c.id === id);
            expect(meta, `Component with id '${id}' not found in registry`).toBeDefined();
            expect(meta.printFallback).toBe(expectedFallback);
        }
    });
    it('medium-priority components have correct printFallback strings', () => {
        const expected = {
            'process-steps': 'All steps visible, checkbox squares for print',
            'reflection-prompt': 'Prompt with write-in lines',
            'student-textbox': 'Lined write-in area',
            'short-answer': 'Question with lined answer space, mark allocation shown'
        };
        for (const [id, expectedFallback] of Object.entries(expected)) {
            const meta = Object.values(componentRegistry).find((c) => c.id === id);
            expect(meta, `Component with id '${id}' not found in registry`).toBeDefined();
            expect(meta.printFallback).toBe(expectedFallback);
        }
    });
    it('low-priority CSS-only components have correct printFallback strings', () => {
        const expected = {
            'diagram-series': 'All diagrams in sequence with step labels',
            'diagram-block': 'Static SVG 80% width centred',
            'pitfall-alert': 'Full static, amber left border',
            'comparison-grid': 'Static comparison table'
        };
        for (const [id, expectedFallback] of Object.entries(expected)) {
            const meta = Object.values(componentRegistry).find((c) => c.id === id);
            expect(meta, `Component with id '${id}' not found in registry`).toBeDefined();
            expect(meta.printFallback).toBe(expectedFallback);
        }
    });
});

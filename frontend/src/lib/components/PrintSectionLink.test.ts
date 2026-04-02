// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { SectionContent } from 'lectio';

vi.mock('qrcode-generator', () => ({
	default: () => ({
		addData: vi.fn(),
		make: vi.fn(),
		createSvgTag: vi.fn(() => '<svg data-testid="qr-svg"></svg>')
	})
}));

import PrintSectionLink from './PrintSectionLink.svelte';

const baseSection: SectionContent = {
	section_id: 's-01',
	template_id: 'guided-concept-path',
	header: {
		title: 'Interactive Section',
		subject: 'Calculus',
		grade_band: 'secondary'
	},
	hook: {
		headline: 'Hook',
		body: 'Body',
		anchor: 'anchor'
	},
	explanation: {
		body: 'Explain',
		emphasis: ['limits']
	},
	practice: {
		problems: []
	},
	what_next: {
		body: 'Next',
		next: 'Continuity'
	},
		simulations: []
};

describe('PrintSectionLink', () => {
	afterEach(() => {
		cleanup();
	});

	it('renders a QR block for interactive sections', () => {
		render(PrintSectionLink, {
			generationId: 'gen-123',
			section: {
				...baseSection,
				quiz: {
					question: 'Which value is the limit?',
					options: [],
					feedback_correct: 'Correct',
					feedback_incorrect: 'Try again'
				}
			}
		});

		expect(screen.getByText(/interactive follow-up/i)).toBeTruthy();
		expect(screen.getByText(/scan to open the live section/i)).toBeTruthy();
		expect(screen.getByText(/textbook\/gen-123#section-s-01/i)).toBeTruthy();
	});

	it('stays hidden for non-interactive sections', () => {
		const { container } = render(PrintSectionLink, {
			generationId: 'gen-123',
			section: baseSection
		});

		expect(container.textContent?.trim()).toBe('');
	});
});

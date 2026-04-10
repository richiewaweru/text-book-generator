import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const HERE = dirname(fileURLToPath(import.meta.url));
const DIAGRAM_LED_LAYOUT = resolve(
	HERE,
	'../../../vendor/lectio/templates/diagram-led/layout.svelte'
);

describe('diagram-led vendor layout source', () => {
	it('renders the callout and summary blocks when those fields are present', () => {
		const source = readFileSync(DIAGRAM_LED_LAYOUT, 'utf8');

		expect(source).toContain('CalloutBlock');
		expect(source).toContain('SummaryBlock');
		expect(source).toContain('{#if section.callout}');
		expect(source).toContain('<CalloutBlock content={section.callout} />');
		expect(source).toContain('{#if section.summary}');
		expect(source).toContain('<SummaryBlock content={section.summary} />');
	});
});

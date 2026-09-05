import { describe, expect, it } from 'vitest';
import { protectCurrencyAmounts, protectCurrencyContent } from './render-content';

describe('Lectio render content preparation', () => {
	it('protects two currency amounts in prose independently', () => {
		const text = 'reduces a $500 balance to $375.';
		expect(protectCurrencyAmounts(text)).toBe('reduces a \\$500 balance to \\$375.');
	});

	it('protects a single currency amount in prose', () => {
		expect(protectCurrencyAmounts('The learner starts with $45.')).toBe(
			'The learner starts with \\$45.'
		);
	});

	it('preserves legitimate inline math', () => {
		const text = 'The equation is $x^2 + y^2$.';
		expect(protectCurrencyAmounts(text)).toBe('The equation is $x^2 + y^2$.');
	});

	it('prepares nested section content without mutating it', () => {
		const content = {
			practice: { problems: [{ question: 'Save $500, then spend $45.' }] },
			formula: '$x + 1 = 2$'
		};

		expect(protectCurrencyContent(content)).toEqual({
			practice: { problems: [{ question: 'Save \\$500, then spend \\$45.' }] },
			formula: '$x + 1 = 2$'
		});
		expect(content.practice.problems[0].question).toBe('Save $500, then spend $45.');
	});
});

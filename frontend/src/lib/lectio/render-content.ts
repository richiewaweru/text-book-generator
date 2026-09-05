const CURRENCY_AMOUNT = /^\$(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?(?=$|[\s.,!?;:)\]}])/;

function isEscaped(text: string, index: number): boolean {
	let backslashes = 0;
	for (let cursor = index - 1; cursor >= 0 && text[cursor] === '\\'; cursor -= 1) {
		backslashes += 1;
	}
	return backslashes % 2 === 1;
}

function nextDelimiter(text: string, start: number): number {
	for (let index = start; index < text.length; index += 1) {
		if (text[index] === '$' && !isEscaped(text, index)) return index;
	}
	return -1;
}

function isLikelyMathExpression(expression: string): boolean {
	const trimmed = expression.trim();
	if (!trimmed || !/[+\-*=/<>]/.test(trimmed)) return false;
	if (/[\\^_{}[\]]/.test(trimmed)) return true;

	// Numeric-first equations can be legitimate math (for example, $500 - x = 375$),
	// while prose amounts normally contain words between dollar-prefixed numbers.
	const words = trimmed.match(/[A-Za-z]+/g) ?? [];
	return words.every((word) => word.length === 1);
}

/**
 * Protect ordinary dollar-prefixed numeric amounts before Lectio parses inline math.
 * The Lectio package owns the markdown/KaTeX renderer, so this is applied once at
 * the shared content boundary rather than in individual component scenarios.
 */
export function protectCurrencyAmounts(text: string): string {
	let result = '';
	let cursor = 0;

	while (cursor < text.length) {
		const dollar = text.indexOf('$', cursor);
		if (dollar === -1) {
			result += text.slice(cursor);
			break;
		}

		result += text.slice(cursor, dollar);
		if (isEscaped(text, dollar)) {
			result += '$';
			cursor = dollar + 1;
			continue;
		}

		const amount = text.slice(dollar).match(CURRENCY_AMOUNT)?.[0];
		if (!amount) {
			result += '$';
			cursor = dollar + 1;
			continue;
		}

		const closing = nextDelimiter(text, dollar + 1);
		const expression = closing === -1 ? '' : text.slice(dollar + 1, closing);
		const isMathDelimiter = closing !== -1 && isLikelyMathExpression(expression);
		result += isMathDelimiter ? amount : `\\${amount}`;
		cursor = dollar + amount.length;
	}

	return result;
}

export function protectCurrencyContent<T>(value: T): T {
	if (typeof value === 'string') return protectCurrencyAmounts(value) as T;
	if (Array.isArray(value)) return value.map((item) => protectCurrencyContent(item)) as T;
	if (!value || typeof value !== 'object') return value;

	return Object.fromEntries(
		Object.entries(value).map(([key, item]) => [key, protectCurrencyContent(item)])
	) as T;
}

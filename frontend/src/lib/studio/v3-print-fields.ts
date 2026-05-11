import type { CanvasSection } from '$lib/types/v3';

export type PrintBlock =
	| { kind: 'h3'; text: string }
	| { kind: 'p'; text: string }
	| { kind: 'ul'; items: string[] }
	| { kind: 'img'; src: string; alt: string };

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function safeText(value: unknown): string {
	if (typeof value === 'string') return value.trim();
	if (typeof value === 'number' && !Number.isNaN(value)) return String(value);
	return '';
}

function pushParagraph(blocks: PrintBlock[], text: string): void {
	const t = text.trim();
	if (t) blocks.push({ kind: 'p', text: t });
}

function pushH3(blocks: PrintBlock[], text: string): void {
	const t = text.trim();
	if (t) blocks.push({ kind: 'h3', text: t });
}

function blocksFromHook(value: unknown): PrintBlock[] {
	const blocks: PrintBlock[] = [];
	if (!isRecord(value)) return blocks;
	pushH3(blocks, safeText(value.headline));
	pushParagraph(blocks, safeText(value.subhead));
	pushParagraph(blocks, safeText(value.body));
	return blocks;
}

function blocksFromReading(value: unknown): PrintBlock[] {
	const blocks: PrintBlock[] = [];
	if (!isRecord(value)) return blocks;
	const body = safeText(value.body);
	if (body) {
		pushParagraph(blocks, body);
		return blocks;
	}
	const arr = value.blocks;
	if (!Array.isArray(arr)) return blocks;
	for (const item of arr) {
		if (!isRecord(item)) continue;
		const t =
			safeText(item.body) || safeText(item.text) || safeText(item.content) || safeText(item.title);
		pushParagraph(blocks, t);
	}
	return blocks;
}

function blocksFromExplanation(value: unknown): PrintBlock[] {
	if (!isRecord(value)) return [];
	const t = safeText(value.body) || safeText(value.text);
	return t ? [{ kind: 'p', text: t }] : [];
}

function blocksFromPractice(value: unknown): PrintBlock[] {
	if (!isRecord(value)) return [];
	const items: string[] = [];
	const problems = value.problems;
	if (Array.isArray(problems)) {
		for (const p of problems) {
			if (!isRecord(p)) continue;
			const line = safeText(p.question) || safeText(p.prompt) || safeText(p.stem);
			if (line) items.push(line);
		}
	}
	const rawItems = value.items;
	if (Array.isArray(rawItems)) {
		for (const p of rawItems) {
			if (!isRecord(p)) continue;
			const line = safeText(p.prompt) || safeText(p.question);
			if (line) items.push(line);
		}
	}
	if (items.length === 0) return [];
	return [{ kind: 'ul', items }];
}

function blocksFromDiagram(value: unknown, altFallback: string): PrintBlock[] {
	if (!isRecord(value)) return [];
	const src = safeText(value.image_url);
	if (!src) return [];
	const alt =
		safeText(value.caption) || safeText(value.title) || safeText(value.alt) || altFallback || 'Figure';
	return [{ kind: 'img', src, alt }];
}

function blocksFromDiagramSeries(value: unknown, altFallback: string): PrintBlock[] {
	if (!isRecord(value)) return [];
	const diagrams = value.diagrams;
	if (!Array.isArray(diagrams)) return [];
	const out: PrintBlock[] = [];
	for (const d of diagrams) {
		out.push(...blocksFromDiagram(d, altFallback));
	}
	return out;
}

/** Named content blocks (alert, model, summary, …): title + body + optional bullet list */
function blocksFromNamedBlock(value: unknown): PrintBlock[] {
	const blocks: PrintBlock[] = [];
	if (!isRecord(value)) return blocks;
	pushH3(blocks, safeText(value.title) || safeText(value.headline));
	pushParagraph(
		blocks,
		safeText(value.body) ||
			safeText(value.text) ||
			safeText(value.statement) ||
			safeText(value.definition) ||
			safeText(value.summary)
	);
	const bullets = value.bullets ?? value.points;
	if (Array.isArray(bullets)) {
		const items = bullets.map(safeText).filter(Boolean);
		if (items.length) blocks.push({ kind: 'ul', items });
	}
	return blocks;
}

const ORDERED_KEYS = [
	'hook',
	'reading',
	'explanation',
	'learning_goal',
	'intro',
	'vocabulary',
	'key_terms',
	'worked_example',
	'alert',
	'model',
	'understand',
	'practice',
	'diagram',
	'diagram_series',
	'summary',
	'reflection',
	'exit_slip',
	'check',
	'quiz'
] as const;

const SKIP_KEYS = new Set(['section_id', 'header']);

export function mergedFieldsToBlocks(
	fields: Record<string, unknown>,
	sectionTitleAlt = ''
): PrintBlock[] {
	const blocks: PrintBlock[] = [];

	for (const key of ORDERED_KEYS) {
		if (!Object.prototype.hasOwnProperty.call(fields, key)) continue;
		const val = fields[key];
		switch (key) {
			case 'hook':
				blocks.push(...blocksFromHook(val));
				break;
			case 'reading':
				blocks.push(...blocksFromReading(val));
				break;
			case 'explanation':
				blocks.push(...blocksFromExplanation(val));
				break;
			case 'practice':
				blocks.push(...blocksFromPractice(val));
				break;
			case 'diagram':
				blocks.push(...blocksFromDiagram(val, sectionTitleAlt));
				break;
			case 'diagram_series':
				blocks.push(...blocksFromDiagramSeries(val, sectionTitleAlt));
				break;
			default:
				if (typeof val === 'string') {
					pushParagraph(blocks, val);
				} else if (
					Array.isArray(val) &&
					val.length > 0 &&
					val.every((x) => typeof x === 'string')
				) {
					const items = (val as string[]).map((s) => s.trim()).filter(Boolean);
					if (items.length) blocks.push({ kind: 'ul', items });
				} else {
					blocks.push(...blocksFromNamedBlock(val));
				}
		}
	}

	const ordered = new Set<string>(ORDERED_KEYS);
	for (const key of Object.keys(fields).sort()) {
		if (SKIP_KEYS.has(key) || ordered.has(key)) continue;
		const val = fields[key];
		if (typeof val === 'string' && val.trim()) {
			pushParagraph(blocks, val);
		} else if (Array.isArray(val) && val.length > 0 && val.every((x) => typeof x === 'string')) {
			const items = (val as string[]).map((s) => s.trim()).filter(Boolean);
			if (items.length) blocks.push({ kind: 'ul', items });
		}
	}

	return blocks;
}

export function blocksForSection(section: CanvasSection): PrintBlock[] {
	return mergedFieldsToBlocks(section.mergedFields, section.title);
}

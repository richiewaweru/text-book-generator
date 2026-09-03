import { validateDocument, type LessonDocument } from 'lectio';

import { exportToLessonDocument } from '$lib/generation/export-document';
import {
	adaptV3PackToLectioDocument,
	type AdaptV3PackOptions,
	type V3PackDocument
} from '$lib/studio/v3-pack-to-lectio-document';
import type { IssueSection } from '$lib/builder/issues';
import { partitionGenerationIssues } from '$lib/builder/generation-issues';

export { partitionGenerationIssues } from '$lib/builder/generation-issues';
export type { GenerationIssuePartition } from '$lib/builder/generation-issues';

export type GenerationPipelineId = 'component_lectio' | 'v3_studio';

const REQUIRED_DOCUMENT_FIELDS = [
	'version',
	'id',
	'title',
	'subject',
	'preset_id',
	'source',
	'sections',
	'blocks',
	'media'
] as const;

const REQUIRED_SECTION_FIELDS = ['id', 'template_id', 'block_ids', 'title', 'position'] as const;

export class LectioDocumentValidationError extends Error {
	errors: string[];
	constructor(errors: string[]) {
		super(errors.join('; '));
		this.name = 'LectioDocumentValidationError';
		this.errors = errors;
	}
}

function structuralLessonDocumentErrors(value: unknown): string[] {
	if (!value || typeof value !== 'object') {
		return ['LessonDocument must be an object'];
	}
	const doc = value as Record<string, unknown>;
	const errors: string[] = [];
	for (const field of REQUIRED_DOCUMENT_FIELDS) {
		if (!(field in doc)) {
			errors.push(`Missing required field: ${field}`);
		}
	}
	if (doc.version !== 1) {
		errors.push(`Unsupported document version: ${String(doc.version)}. Expected 1.`);
	}
	if (!Array.isArray(doc.sections)) {
		errors.push('sections must be an array');
		return errors;
	}
	if (typeof doc.blocks !== 'object' || doc.blocks === null || Array.isArray(doc.blocks)) {
		errors.push('blocks must be an object');
		return errors;
	}
	for (let i = 0; i < doc.sections.length; i++) {
		const section = doc.sections[i] as Record<string, unknown> | null;
		if (!section || typeof section !== 'object') {
			errors.push(`sections[${i}] must be an object`);
			continue;
		}
		for (const field of REQUIRED_SECTION_FIELDS) {
			if (!(field in section)) {
				errors.push(`sections[${i}] missing required field: ${field}`);
			}
		}
	}
	return errors;
}

export function assertCanonicalLessonDocument(value: unknown): LessonDocument {
	const errors = structuralLessonDocumentErrors(value);
	if (errors.length) {
		throw new LectioDocumentValidationError(errors);
	}
	const lesson = value as LessonDocument;
	const validation = validateDocument(lesson);
	if (validation && typeof validation === 'object' && 'valid' in validation && validation.valid === false) {
		const details = Array.isArray(validation.errors) ? validation.errors : ['invalid LessonDocument'];
		throw new LectioDocumentValidationError(details.map(String));
	}
	return lesson;
}

/**
 * Open a generation in Builder.
 *
 * component_lectio → canonical LessonDocument directly (no V3 pack adapter).
 * v3_studio / unmarked → existing V3 pack adapter.
 */
export function generationToBuilderDocument(
	payload: V3PackDocument | LessonDocument | Record<string, unknown>,
	options: AdaptV3PackOptions & { pipeline?: GenerationPipelineId | string | null } = {}
): LessonDocument {
	const pipeline = options.pipeline ?? null;
	if (pipeline === 'component_lectio') {
		const nested = (payload as Record<string, unknown>).lesson_document;
		const candidate = payload;
		if (nested && typeof nested === 'object') {
			return assertCanonicalLessonDocument(nested);
		}
		return assertCanonicalLessonDocument(candidate);
	}
	return v3PackToBuilderDocument(payload as V3PackDocument, options);
}

export function v3PackToBuilderDocument(
	pack: V3PackDocument,
	options: AdaptV3PackOptions = {}
): LessonDocument {
	const generationDoc = adaptV3PackToLectioDocument(pack, options);
	const lesson = exportToLessonDocument(generationDoc);
	const { sectionIssues } = partitionGenerationIssues(pack, lesson.sections.map((section) => section.id));
	return {
		...lesson,
		sections: lesson.sections.map((section) => {
			const issues = sectionIssues[section.id] ?? [];
			return issues.length ? ({ ...section, meta: { issues } } as IssueSection) : section;
		})
	};
}

import type { LessonDocument } from 'lectio';

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

function isLessonDocumentLike(value: unknown): value is LessonDocument {
	if (!value || typeof value !== 'object') return false;
	const doc = value as Record<string, unknown>;
	return (
		(doc.schema === 'LessonDocument' || Array.isArray(doc.sections)) &&
		typeof doc.blocks === 'object' &&
		doc.blocks !== null
	);
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
	if (pipeline === 'component_lectio' || (pipeline == null && isLessonDocumentLike(payload))) {
		if (isLessonDocumentLike(payload)) {
			return payload as LessonDocument;
		}
		const nested = (payload as Record<string, unknown>).lesson_document;
		if (isLessonDocumentLike(nested)) {
			return nested as LessonDocument;
		}
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

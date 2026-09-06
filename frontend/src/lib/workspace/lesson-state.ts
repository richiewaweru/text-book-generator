import type { LessonDocument } from 'lectio';

import type { BuilderIssue, IssueSection } from '$lib/builder/issues';
import type { BuilderLessonSummary } from '$lib/builder/api/lesson-crud';

export type LessonState = 'writing' | 'attention' | 'ready' | 'draft';

export interface LessonRow {
	id: string;
	title: string;
	classLabel: string | null;
	subject: string | null;
	state: LessonState;
	sectionsDone: number | null;
	sectionsTotal: number | null;
	flagCount: number;
	awaitingReview: boolean;
	updatedAt: string;
	href: string;
}

export interface DeriveLessonRowsInput {
	lessons: BuilderLessonSummary[];
	lessonDocumentsById?: Record<string, LessonDocument | undefined>;
	dismissedIssueIdsByLessonId?: Record<string, string[] | undefined>;
}

function allLessonIssues(document: LessonDocument | undefined): BuilderIssue[] {
	if (!document) return [];
	return document.sections.flatMap((section) => (section as IssueSection).meta?.issues ?? []);
}

function unresolvedFlagCount(
	lessonDocument: LessonDocument | undefined,
	dismissedIssueIds: string[]
): number {
	const dismissed = new Set(dismissedIssueIds);
	const persisted = allLessonIssues(lessonDocument);
	return new Set(
		persisted
			.filter((issue) => !issue.resolved && !dismissed.has(issue.id))
			.map((issue) => issue.id)
	).size;
}

export function deriveLessonRows({
	lessons,
	lessonDocumentsById = {},
	dismissedIssueIdsByLessonId = {}
}: DeriveLessonRowsInput): LessonRow[] {
	return lessons
		.map((lesson): LessonRow => {
			const flags = unresolvedFlagCount(
				lessonDocumentsById[lesson.id],
				dismissedIssueIdsByLessonId[lesson.id] ?? []
			);
			const document = lessonDocumentsById[lesson.id];
			const sectionCount = document?.sections.length ?? 0;
			const generated = lesson.source_type === 'component_lectio' && Boolean(lesson.source_generation_id);
			const state: LessonState = !generated
				? 'draft'
				: flags > 0
					? 'attention'
					: sectionCount > 0
						? 'ready'
						: 'draft';

			return {
				id: lesson.id,
				title: lesson.title || 'Untitled lesson',
				classLabel: lesson.class_label,
				subject: document?.subject ?? null,
				state,
				sectionsDone: generated ? sectionCount : null,
				sectionsTotal: generated ? sectionCount : null,
				flagCount: flags,
				awaitingReview: false,
				updatedAt: lesson.updated_at,
				href: `/builder/${lesson.id}`
			};
		})
		.sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt));
}

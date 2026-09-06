import type { LessonDocument } from 'lectio';
import { describe, expect, it } from 'vitest';
import type { BuilderLessonSummary } from '$lib/builder/api/lesson-crud';
import { deriveLessonRows } from './lesson-state';

const generated: BuilderLessonSummary = {
	id: 'generated', source_generation_id: 'generation-1', source_type: 'component_lectio',
	title: 'Photosynthesis', class_label: 'Year 7 Science', created_at: '2026-07-27T08:00:00Z', updated_at: '2026-07-27T10:00:00Z'
};
const document = {
	version: 1, id: 'generated', title: 'Photosynthesis', subject: 'Science',
	sections: [{ id: 'section-1' }], blocks: {}, media: {}
} as unknown as LessonDocument;

describe('deriveLessonRows', () => {
	it('derives canonical generated and manual lesson states without pipeline snapshots', () => {
		const rows = deriveLessonRows({
			lessons: [generated, { ...generated, id: 'draft', source_generation_id: null, source_type: 'manual', title: 'Draft' }],
			lessonDocumentsById: { generated: document, draft: { ...document, id: 'draft', sections: [] } }
		});
		expect(rows.map((row) => [row.id, row.state])).toEqual([
			['generated', 'ready'], ['draft', 'draft']
		]);
		expect(rows[0]).toMatchObject({ subject: 'Science', sectionsDone: 1, sectionsTotal: 1, href: '/builder/generated' });
	});

	it('shows unresolved document issues as attention and honors dismissal', () => {
		const withIssue = {
			...document,
			sections: [{ id: 'section-1', meta: { issues: [{ id: 'issue-1', resolved: false, severity: 'minor', message: 'Review', kind: 'quality' }] } }]
		} as unknown as LessonDocument;
		expect(deriveLessonRows({ lessons: [generated], lessonDocumentsById: { generated: withIssue } })[0]?.state).toBe('attention');
		expect(deriveLessonRows({ lessons: [generated], lessonDocumentsById: { generated: withIssue }, dismissedIssueIdsByLessonId: { generated: ['issue-1'] } })[0]?.state).toBe('ready');
	});
});

import type { CanvasSection } from '$lib/types/v3';

export function mapPackSectionsToCanvas(sections: unknown[]): CanvasSection[] {
	return sections.map((raw, index) => {
		const section = typeof raw === 'object' && raw !== null ? (raw as Record<string, unknown>) : {};
		const header =
			typeof section.header === 'object' && section.header !== null
				? (section.header as Record<string, unknown>)
				: null;
		const headerTitle = typeof header?.title === 'string' ? header.title : '';
		const fallbackTitle = typeof section.title === 'string' ? section.title : '';
		const sectionId = section.section_id ?? `section-${index + 1}`;
		return {
			id: String(sectionId),
			title: headerTitle || fallbackTitle || `Section ${index + 1}`,
			teacher_labels: '',
			order: index,
			components: [],
			visual: null,
			questions: [],
			mergedFields: section
		};
	});
}


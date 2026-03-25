import type { SectionContent } from 'lectio';

import { parseIncomingSection } from '$lib/parse-section';
import type {
	FailedSectionEntry,
	GenerationDocument,
	PipelineSectionManifestItem,
	SectionFailedEvent,
	SectionReadyEvent,
	SectionStartedEvent
} from '$lib/types';

export interface ViewerWarning {
	message: string;
}

export interface ViewerSectionSlot {
	section_id: string;
	title: string;
	position: number;
	status: 'ready' | 'pending' | 'failed';
	section: SectionContent | null;
}

function sortManifest(
	manifest: PipelineSectionManifestItem[] | undefined
): PipelineSectionManifestItem[] {
	const byId = new Map<string, PipelineSectionManifestItem>();
	for (const item of manifest ?? []) {
		byId.set(item.section_id, item);
	}
	return [...byId.values()].sort(
		(left, right) => left.position - right.position || left.section_id.localeCompare(right.section_id)
	);
}

function sortSectionsByManifest(
	sections: SectionContent[],
	manifest: PipelineSectionManifestItem[]
): SectionContent[] {
	if (manifest.length === 0) {
		return sections;
	}

	const positions = new Map(manifest.map((item) => [item.section_id, item.position]));
	const fallbackPosition = manifest.length + 1;
	return [...sections].sort((left, right) => {
		const leftPosition = positions.get(left.section_id) ?? fallbackPosition;
		const rightPosition = positions.get(right.section_id) ?? fallbackPosition;
		return leftPosition - rightPosition || left.section_id.localeCompare(right.section_id);
	});
}

function sortFailedSections(
	failedSections: FailedSectionEntry[],
	manifest: PipelineSectionManifestItem[]
): FailedSectionEntry[] {
	const positions = new Map(manifest.map((item) => [item.section_id, item.position]));
	const fallbackPosition = manifest.length + 1;
	return [...failedSections].sort((left, right) => {
		const leftPosition = positions.get(left.section_id) ?? left.position ?? fallbackPosition;
		const rightPosition = positions.get(right.section_id) ?? right.position ?? fallbackPosition;
		return leftPosition - rightPosition || left.section_id.localeCompare(right.section_id);
	});
}

export function normalizeDocument(document: GenerationDocument): GenerationDocument {
	const section_manifest = sortManifest(document.section_manifest);
	return {
		...document,
		section_manifest,
		sections: sortSectionsByManifest(document.sections, section_manifest),
		failed_sections: sortFailedSections(document.failed_sections ?? [], section_manifest)
	};
}

export function applySectionStarted(
	document: GenerationDocument,
	payload: SectionStartedEvent
): GenerationDocument {
	return normalizeDocument({
		...document,
		status: 'running',
		updated_at: new Date().toISOString(),
		section_manifest: [
			...document.section_manifest,
			{
				section_id: payload.section_id,
				title: payload.title,
				position: payload.position
			}
		]
	});
}

export function applySectionReady(
	document: GenerationDocument,
	payload: Pick<SectionReadyEvent, 'section' | 'section_id'>
): { document: GenerationDocument; warning: ViewerWarning | null } {
	try {
		const section = parseIncomingSection(payload.section);
		const sections = [...document.sections];
		const existingIndex = sections.findIndex((entry) => entry.section_id === section.section_id);
		if (existingIndex >= 0) {
			sections[existingIndex] = section;
		} else {
			sections.push(section);
		}

		return {
			document: normalizeDocument({
				...document,
				status: 'running',
				updated_at: new Date().toISOString(),
				sections,
				failed_sections: document.failed_sections.filter(
					(entry) => entry.section_id !== payload.section_id
				)
			}),
			warning: null
		};
	} catch (error) {
		return {
			document,
			warning: {
				message:
					error instanceof Error
						? error.message
						: '[Lectio] Invalid section from pipeline.'
			}
		};
	}
}

export function applySectionFailed(
	document: GenerationDocument,
	payload: SectionFailedEvent
): GenerationDocument {
	const failedSections = [...document.failed_sections];
	const nextFailed: FailedSectionEntry = {
		section_id: payload.section_id,
		title: payload.title,
		position: payload.position,
		focus: payload.focus ?? null,
		bridges_from: payload.bridges_from ?? null,
		bridges_to: payload.bridges_to ?? null,
		needs_diagram: payload.needs_diagram,
		needs_worked_example: payload.needs_worked_example,
		failed_at_node: payload.failed_at_node,
		error_type: payload.error_type,
		error_summary: payload.error_summary,
		attempt_count: payload.attempt_count,
		can_retry: payload.can_retry,
		missing_components: payload.missing_components,
		failure_detail: payload.failure_detail ?? null
	};
	const existingIndex = failedSections.findIndex((entry) => entry.section_id === payload.section_id);
	if (existingIndex >= 0) {
		failedSections[existingIndex] = nextFailed;
	} else {
		failedSections.push(nextFailed);
	}

	return normalizeDocument({
		...document,
		status: 'running',
		updated_at: new Date().toISOString(),
		failed_sections: failedSections
	});
}

export function buildSectionSlots(
	document: GenerationDocument | null,
	sectionCount: number | null
): ViewerSectionSlot[] {
	if (!document && !sectionCount) {
		return [];
	}

	const normalized = document ? normalizeDocument(document) : null;
	const manifest = normalized?.section_manifest ?? [];
	const readySections = normalized?.sections ?? [];
	const failedSections = normalized?.failed_sections ?? [];
	const readyById = new Map(readySections.map((section) => [section.section_id, section]));
	const failedById = new Map(failedSections.map((section) => [section.section_id, section]));

	if (manifest.length > 0) {
		const manifestIds = new Set(manifest.map((item) => item.section_id));
		const slots = manifest.map((item) => ({
			section_id: item.section_id,
			title: item.title,
			position: item.position,
			status: readyById.has(item.section_id)
				? 'ready'
				: failedById.has(item.section_id)
					? 'failed'
					: 'pending',
			section: readyById.get(item.section_id) ?? null
		})) satisfies ViewerSectionSlot[];
		const orphanSections = readySections
			.filter((section) => !manifestIds.has(section.section_id))
			.map((section, index) => ({
				section_id: section.section_id,
				title: section.header.title,
				position: manifest.length + index + 1,
				status: 'ready' as const,
				section
			}));
		const orphanFailures = failedSections
			.filter((section) => !manifestIds.has(section.section_id))
			.map((section, index) => ({
				section_id: section.section_id,
				title: section.title,
				position: manifest.length + orphanSections.length + index + 1,
				status: 'failed' as const,
				section: null
			}));
		return [...slots, ...orphanSections, ...orphanFailures];
	}

	const total = Math.max(sectionCount ?? 0, readySections.length, failedSections.length);
	return Array.from({ length: total }, (_, index) => {
		const section = readySections[index] ?? null;
		const failed = failedSections[index] ?? null;
		return {
			section_id: section?.section_id ?? failed?.section_id ?? `pending-${index + 1}`,
			title: section?.header.title ?? failed?.title ?? `Section ${index + 1}`,
			position: index + 1,
			status: section ? 'ready' : failed ? 'failed' : 'pending',
			section
		};
	});
}

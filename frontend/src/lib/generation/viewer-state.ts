import type { SectionContent } from 'lectio';

import { parseIncomingSection } from '$lib/parse-section';
import type {
	GenerationDocument,
	PipelineSectionManifestItem,
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
	status: 'ready' | 'pending';
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

export function normalizeDocument(document: GenerationDocument): GenerationDocument {
	const section_manifest = sortManifest(document.section_manifest);
	return {
		...document,
		section_manifest,
		sections: sortSectionsByManifest(document.sections, section_manifest)
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
				sections
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
	const readyById = new Map(readySections.map((section) => [section.section_id, section]));

	if (manifest.length > 0) {
		const manifestIds = new Set(manifest.map((item) => item.section_id));
		const slots = manifest.map((item) => ({
			section_id: item.section_id,
			title: item.title,
			position: item.position,
			status: readyById.has(item.section_id) ? 'ready' : 'pending',
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
		return [...slots, ...orphanSections];
	}

	const total = Math.max(sectionCount ?? 0, readySections.length);
	return Array.from({ length: total }, (_, index) => {
		const section = readySections[index] ?? null;
		return {
			section_id: section?.section_id ?? `pending-${index + 1}`,
			title: section?.header.title ?? `Section ${index + 1}`,
			position: index + 1,
			status: section ? 'ready' : 'pending',
			section
		};
	});
}

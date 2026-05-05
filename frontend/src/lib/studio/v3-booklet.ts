import type { BookletStatus } from '$lib/types/v3';

export function isBookletStatus(value: unknown): value is BookletStatus {
	return (
		value === 'streaming_preview' ||
		value === 'draft_ready' ||
		value === 'draft_with_warnings' ||
		value === 'draft_needs_review' ||
		value === 'final_ready' ||
		value === 'final_with_warnings' ||
		value === 'failed_unusable'
	);
}

export function getBookletExportPolicy(status: BookletStatus): {
	enabled: boolean;
	label: string;
	requiresConfirm: boolean;
} {
	switch (status) {
		case 'final_ready':
			return { enabled: true, label: 'Download Final PDF', requiresConfirm: false };
		case 'final_with_warnings':
			return { enabled: true, label: 'Download Final PDF (Warnings)', requiresConfirm: false };
		case 'draft_ready':
			return { enabled: true, label: 'Download Draft PDF', requiresConfirm: false };
		case 'draft_with_warnings':
			return { enabled: true, label: 'Download Draft PDF (Warnings)', requiresConfirm: false };
		case 'draft_needs_review':
			return { enabled: true, label: 'Download Draft PDF (Review Needed)', requiresConfirm: true };
		default:
			return { enabled: false, label: 'Export Unavailable', requiresConfirm: false };
	}
}

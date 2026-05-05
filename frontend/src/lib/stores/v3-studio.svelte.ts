import type {
	BlueprintPreviewDTO,
	BookletStatus,
	CanvasSection,
	V3DraftPack,
	V3ClarificationAnswer,
	V3ClarificationQuestion,
	V3InputForm,
	V3SignalSummary,
	V3Stage
} from '$lib/types/v3';

export type V3StudioStore = {
	stage: V3Stage;
	form: V3InputForm | null;
	signals: V3SignalSummary | null;
	clarifications: V3ClarificationQuestion[];
	answers: V3ClarificationAnswer[];
	blueprint: BlueprintPreviewDTO | null;
	/** Active v3 generation id after approve (used for PDF export). */
	generationId: string | null;
	canvas: CanvasSection[];
	draftPack: V3DraftPack | null;
	finalPack: V3DraftPack | null;
	activePack: V3DraftPack | null;
	bookletStatus: BookletStatus;
	bookletIssues: Array<Record<string, unknown>>;
	error: string | null;
	coherenceHint: string | null;
	streamCancel: (() => void) | null;
};

export const v3Studio = $state<V3StudioStore>({
	stage: 'input',
	form: null,
	signals: null,
	clarifications: [],
	answers: [],
	blueprint: null,
	generationId: null,
	canvas: [],
	draftPack: null,
	finalPack: null,
	activePack: null,
	bookletStatus: 'streaming_preview',
	bookletIssues: [],
	error: null,
	coherenceHint: null,
	streamCancel: null
});

export function resetV3Studio(): void {
	v3Studio.streamCancel?.();
	v3Studio.stage = 'input';
	v3Studio.form = null;
	v3Studio.signals = null;
	v3Studio.clarifications = [];
	v3Studio.answers = [];
	v3Studio.blueprint = null;
	v3Studio.generationId = null;
	v3Studio.canvas = [];
	v3Studio.draftPack = null;
	v3Studio.finalPack = null;
	v3Studio.activePack = null;
	v3Studio.bookletStatus = 'streaming_preview';
	v3Studio.bookletIssues = [];
	v3Studio.error = null;
	v3Studio.coherenceHint = null;
	v3Studio.streamCancel = null;
}

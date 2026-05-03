<script lang="ts">
	import { connectV3GenerateStream } from '$lib/api/client';

	const CANONICAL_COMPONENT_MAP: Record<string, string> = {
		concept_intro: 'explanation-block',
		worked_example: 'worked-example-card',
		guided_questions: 'practice-stack',
		key_takeaways: 'summary-block',
		retrieval_prompt_set: 'quiz-check',
		problem_set: 'practice-stack',
		misconception_probe: 'interview-anchor',
		area_model_sequence: 'diagram-series',
		focused_questions: 'practice-stack',
		quick_check: 'quiz-check',
		context_overview: 'hook-hero',
		stage_explanations: 'explanation-block',
		diagram_series: 'diagram-series',
		short_questions: 'practice-stack',
		recap: 'summary-block'
	};

	function safeRandomId(prefix: string) {
		if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
			return `${prefix}-${crypto.randomUUID()}`;
		}
		return `${prefix}-${Date.now()}`;
	}

	function canonicalComponentId(slug: string): string {
		if (CANONICAL_COMPONENT_MAP[slug]) return CANONICAL_COMPONENT_MAP[slug];
		if (slug.includes('-')) return slug;
		return 'explanation-block';
	}

	type ComponentSlot = {
		slug: string;
		canonicalId: string;
		label: string;
		status: 'pending' | 'ready' | 'patched';
		data: unknown;
	};

	type SectionSkeleton = {
		sectionId: string;
		title: string;
		components: ComponentSlot[];
		visual?: { status: 'pending' | 'ready'; url: string | null; frames: Record<number, string> };
	};

	const defaultBlueprint = {
		metadata: { version: '3.0', title: 'Demo', subject: 'Math' },
		lesson: { lesson_mode: 'first_exposure', resource_type: 'lesson' },
		applied_lenses: [{ lens_id: 'first_exposure', effects: ['scaffold worked examples'] }],
		voice: { register: 'simple', tone: 'supportive' },
		anchor: { reuse_scope: 'entire_resource' },
		sections: [
			{
				section_id: 'intro',
				title: 'Introduction',
				role: 'orient',
				visual_required: true,
				components: [
					{ component: 'concept_intro', content_intent: 'Define the idea.' },
					{ component: 'worked_example', content_intent: 'Model a solution.' }
				]
			}
		],
		question_plan: [
			{
				question_id: 'q1',
				section_id: 'intro',
				temperature: 'warm',
				prompt: 'Try this',
				expected_answer: '42',
				diagram_required: false
			}
		],
		visual_strategy: {
			visuals: [
				{ section_id: 'intro', strategy: 'supporting diagram', density: 'high' }
			]
		},
		answer_key: { style: 'answers_only' },
		teacher_materials: [],
		prior_knowledge: []
	};

	let blueprintText = $state(JSON.stringify(defaultBlueprint, null, 2));
	let templateId = $state('diagram-led');
	let generationId = $state(safeRandomId('v3-demo'));
	let blueprintId = $state('blueprint-demo');
	let skeleton = $state<SectionSkeleton[]>([]);
	let logLines = $state<string[]>([]);
	let running = $state(false);
	let cancel: (() => void) | null = null;

	function buildSkeleton(blueprint: Record<string, unknown>): SectionSkeleton[] {
		const sections = (blueprint.sections as Array<Record<string, unknown>>) ?? [];
		return sections.map((section) => {
			const components = (section.components as Array<Record<string, unknown>>) ?? [];
			return {
				sectionId: String(section.section_id ?? ''),
				title: String(section.title ?? ''),
				components: components.map((c) => {
					const slug = String(c.component ?? '');
					return {
						slug,
						canonicalId: canonicalComponentId(slug),
						label: slug.replaceAll('_', ' '),
						status: 'pending' as const,
						data: null
					};
				}),
				visual: section.visual_required
					? { status: 'pending', url: null, frames: {} }
					: undefined
			};
		});
	}

	function fillComponent(sectionId: string, componentId: string, data: unknown) {
		skeleton = skeleton.map((section) => {
			if (section.sectionId !== sectionId) return section;
			return {
				...section,
				components: section.components.map((slot) =>
					slot.slug === componentId || slot.canonicalId === componentId
						? { ...slot, status: 'ready', data }
						: slot
				)
			};
		});
	}

	function patchComponent(sectionId: string, componentId: string, data: unknown) {
		skeleton = skeleton.map((section) => {
			if (section.sectionId !== sectionId) return section;
			return {
				...section,
				components: section.components.map((slot) =>
					slot.slug === componentId || slot.canonicalId === componentId
						? { ...slot, status: 'patched', data }
						: slot
				)
			};
		});
	}

	function fillVisual(attachesTo: string, imageUrl: string | null | undefined, frameIndex: number | null) {
		if (!imageUrl) return;
		skeleton = skeleton.map((section) => {
			if (section.sectionId !== attachesTo || !section.visual) return section;
			if (frameIndex === null || frameIndex === undefined) {
				return { ...section, visual: { ...section.visual, status: 'ready', url: imageUrl, frames: {} } };
			}
			return {
				...section,
				visual: {
					...section.visual,
					status: 'ready',
					url: section.visual.url,
					frames: { ...section.visual.frames, [frameIndex]: imageUrl }
				}
			};
		});
	}

	function handleStreamEvent(eventType: string, raw: string) {
		try {
			const payload = JSON.parse(raw) as Record<string, unknown>;
			logLines = [...logLines, `${eventType}: ${raw.slice(0, 120)}`].slice(-40);
			switch (eventType) {
				case 'component_ready':
					fillComponent(
						String(payload.section_id ?? ''),
						String(payload.component_id ?? ''),
						payload.data
					);
					break;
				case 'visual_ready':
					fillVisual(
						String(payload.attaches_to ?? ''),
						payload.image_url as string | undefined,
						(payload.frame_index as number | null) ?? null
					);
					break;
				case 'component_patched':
					patchComponent(
						String(payload.section_id ?? ''),
						String(payload.component_id ?? ''),
						payload.data
					);
					break;
				case 'generation_complete':
				case 'error':
				case 'generation_warning':
					running = false;
					cancel = null;
					break;
				default:
					break;
			}
		} catch {
			logLines = [...logLines, `${eventType}: ${raw}`].slice(-40);
		}
	}

	function startGeneration() {
		cancel?.();
		logLines = [];
		let parsed: Record<string, unknown>;
		try {
			parsed = JSON.parse(blueprintText) as Record<string, unknown>;
		} catch (err) {
			logLines = [`Invalid JSON: ${err instanceof Error ? err.message : String(err)}`];
			return;
		}
		skeleton = buildSkeleton(parsed);
		running = true;
		cancel = connectV3GenerateStream(
			{
				generation_id: generationId,
				blueprint_id: blueprintId,
				template_id: templateId,
				blueprint: parsed
			},
			{
				onOpen: () => logLines.push('stream open'),
				onEvent: (type, data) => handleStreamEvent(type, data),
				onError: (err) => {
					cancel = null;
					running = false;
					logLines = [...logLines, `stream closed: ${String(err)}`];
				}
			}
		);
	}

	function stopGeneration() {
		cancel?.();
		cancel = null;
		running = false;
		logLines = [...logLines, 'cancelled manually'];
	}
</script>

<div class="page">
	<h1>v3 execution canvas (demo)</h1>
	<p class="muted">
		Paste a ProductionBlueprint JSON, then generate. Skeleton renders immediately; SSE events fill slots.
	</p>

	<div class="controls">
		<label>
			Template ID
			<input bind:value={templateId} />
		</label>
		<label>
			Generation ID
			<input bind:value={generationId} />
		</label>
		<label>
			Blueprint ID
			<input bind:value={blueprintId} />
		</label>
		<button type="button" onclick={startGeneration} disabled={running}>Generate</button>
		<button type="button" class="ghost" onclick={stopGeneration}>Stop</button>
	</div>

	<label class="block">
		Blueprint JSON
		<textarea bind:value={blueprintText} rows="14"></textarea>
	</label>

	<section class="layout">
		<div class="canvas">
			<h2>Blueprint skeleton</h2>
			{#if skeleton.length === 0}
				<p class="muted">No skeleton yet.</p>
			{:else}
				{#each skeleton as section}
					<article class="section-card">
						<header>{section.title} <span class="muted">({section.sectionId})</span></header>
						{#each section.components as slot}
							<div class="component" class:ready={slot.status === 'ready'} class:patched={slot.status === 'patched'}>
								<strong>{slot.label}</strong>
								{#if slot.data}
									<pre>{JSON.stringify(slot.data, null, 2)}</pre>
								{:else}
									<p class="muted">waiting…</p>
								{/if}
							</div>
						{/each}
						{#if section.visual}
							<div class="visual">
								<h3>Visual</h3>
								{#if section.visual.url}
									<img src={section.visual.url} alt="" />
								{/if}
								{#each Object.entries(section.visual.frames) as [frame, url]}
									<img src={url} alt={`frame ${frame}`} />
								{/each}
							</div>
						{/if}
					</article>
				{/each}
			{/if}
		</div>
		<div class="log">
			<h2>SSE log</h2>
			<ul>
				{#each logLines as line}
					<li>{line}</li>
				{/each}
			</ul>
		</div>
	</section>
</div>

<style>
	.page {
		padding: 1.5rem;
		max-width: 1200px;
		margin: 0 auto;
		display: grid;
		gap: 1rem;
	}
	textarea {
		width: 100%;
		font-family: var(--font-mono);
		font-size: 0.85rem;
	}
	.controls {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		align-items: flex-end;
	}
	label {
		display: grid;
		gap: 0.25rem;
		font-weight: 600;
		font-size: 0.85rem;
	}
	.block {
		width: 100%;
	}
	.layout {
		display: grid;
		grid-template-columns: minmax(0, 3fr) minmax(260px, 1fr);
		gap: 1rem;
	}
	button {
		border: none;
		background: #2563eb;
		color: #fff;
		padding: 0.65rem 1rem;
		border-radius: 0.35rem;
		cursor: pointer;
	}
	button.ghost {
		background: #e5e7eb;
		color: #111827;
	}
	button:disabled {
		opacity: 0.55;
		cursor: not-allowed;
	}
	.section-card {
		border: 1px solid #e5e7eb;
		padding: 0.85rem;
		border-radius: 0.65rem;
		margin-bottom: 0.85rem;
		background: #fff;
		box-shadow: 0 10px 30px rgb(15 23 42 / 0.05);
	}
	header {
		font-weight: 700;
		margin-bottom: 0.5rem;
	}
	.component {
		border-left: 3px solid #d1d5db;
		padding: 0.5rem;
		margin: 0.4rem 0;
		transition: border-color 0.3s ease, background-color 0.3s ease;
	}
	.component.ready {
		border-left-color: #2563eb;
	}
	.component.patched {
		border-left-color: #ea580c;
		background-color: rgb(251 243 227 / 0.7);
	}
	pre {
		white-space: pre-wrap;
		font-size: 0.82rem;
		background: #f9fafb;
		padding: 0.4rem;
		border-radius: 0.4rem;
	}
	img {
		max-width: 240px;
		border-radius: 0.35rem;
		display: inline-block;
		margin-right: 0.4rem;
	}
	.visual {
		margin-top: 0.65rem;
	}
	.log {
		border: 1px dashed #cbd5f5;
		padding: 0.75rem;
		border-radius: 0.5rem;
		background: #f8fafc;
		max-height: 640px;
		overflow-y: auto;
	}
	ul {
		list-style: none;
		padding-left: 0;
		display: grid;
		gap: 0.25rem;
		font-size: 0.82rem;
		font-family: var(--font-mono);
	}
	.muted {
		color: #6b7280;
		font-size: 0.9rem;
	}
</style>

<script lang="ts">
	import { get } from 'svelte/store';

	import { contracts, editedSpec, planDraft, planningMs, updateSection } from '$lib/stores/studio';
	import type { StudioTemplateContract } from '$lib/types';

	interface Props {
		busy?: boolean;
		onBack: () => void;
		onCommit: () => void;
		onTemplateSwap: (contract: StudioTemplateContract) => void;
		errorMessage?: string | null;
	}

	let { busy = false, onBack, onCommit, onTemplateSwap, errorMessage = null }: Props = $props();

	function handleTitleInput(sectionId: string, title: string) {
		updateSection(sectionId, (section) => ({
			...section,
			title
		}));
	}

	function handleFocusInput(sectionId: string, focusNote: string) {
		updateSection(sectionId, (section) => ({
			...section,
			focus_note: focusNote || null
		}));
	}

	function formatElapsed(ms: number): string {
		if (!ms) return 'Just now';
		return `${(ms / 1000).toFixed(1)}s`;
	}

	function selectedTemplateId(): string {
		return get(editedSpec)?.template_id ?? '';
	}
</script>

{#if $editedSpec}
	<section class="review-shell">
		<div class="review-header">
			<div>
				<p class="eyebrow">Review</p>
				<h2>Approve the plan before generation</h2>
				<p class="lede">
					Check the template choice, edit the section language, then commit the exact plan that
					should drive generation.
				</p>
			</div>
			<div class="review-meta">
				<span class="meta-pill">{$editedSpec.sections.length} sections</span>
				<span class="meta-pill">Planned in {formatElapsed($planningMs)}</span>
			</div>
		</div>

		{#if errorMessage}
			<p class="notice notice-error">{errorMessage}</p>
		{/if}

		{#if $planDraft.error}
			<p class="notice notice-warn">{$planDraft.error}</p>
		{/if}

		{#if $editedSpec.warning}
			<p class="notice notice-warn">{$editedSpec.warning}</p>
		{/if}

		<section class="summary-panel">
			<div>
				<p class="label">Chosen template</p>
				<h3>{$editedSpec.template_decision.chosen_name}</h3>
				<p>{$editedSpec.lesson_rationale}</p>
			</div>
			<div class="summary-side">
				<span class="score-pill">
					Fit {$editedSpec.template_decision.fit_score.toFixed(2)}
				</span>
				<p class="small-copy">{$editedSpec.template_decision.rationale}</p>
			</div>
		</section>

		<section class="template-panel">
			<div class="template-panel-header">
				<div>
					<p class="label">Swap template</p>
					<h3>Try another Lectio shape</h3>
				</div>
				<p class="small-copy">This stays client-side until you commit.</p>
			</div>

			<div class="template-grid">
				{#each $contracts as contract}
					<button
						type="button"
						class:template-selected={selectedTemplateId() === contract.id}
						class="template-option"
						onclick={() => onTemplateSwap(contract)}
						disabled={busy}
					>
						<div class="template-option-topline">
							<strong>{contract.name}</strong>
							<span>{contract.family}</span>
						</div>
						<p>{contract.tagline}</p>
					</button>
				{/each}
			</div>
		</section>

		<section class="section-panel">
			<div class="template-panel-header">
				<div>
					<p class="label">Section plan</p>
					<h3>Edit the wording</h3>
				</div>
				<p class="small-copy">Titles and focus notes are editable before commit.</p>
			</div>

			<div class="section-list">
				{#each $editedSpec.sections as section}
					<article class="section-card">
						<div class="section-card-topline">
							<div class="section-heading">
								<span class="order-pill">0{section.order}</span>
								<span class="role-pill">{section.role}</span>
							</div>
							<div class="component-list">
								{#each section.selected_components as component}
									<span>{component}</span>
								{/each}
							</div>
						</div>

						<label class="field">
							<span>Section title</span>
							<input
								type="text"
								value={section.title}
								oninput={(event) =>
									handleTitleInput(section.id, (event.currentTarget as HTMLInputElement).value)}
								disabled={busy}
							/>
						</label>

						<label class="field">
							<span>Focus note</span>
							<textarea
								rows="3"
								value={section.focus_note ?? section.objective ?? ''}
								oninput={(event) =>
									handleFocusInput(section.id, (event.currentTarget as HTMLTextAreaElement).value)}
								disabled={busy}
							></textarea>
						</label>
					</article>
				{/each}
			</div>
		</section>

		<div class="actions">
			<button class="secondary-button" type="button" onclick={onBack} disabled={busy}>
				Refine brief
			</button>
			<button class="primary-button" type="button" onclick={onCommit} disabled={busy}>
				{busy ? 'Starting generation...' : 'Commit and generate'}
			</button>
		</div>
	</section>
{/if}

<style>
	.review-shell {
		display: grid;
		gap: 1rem;
	}

	.review-header,
	.review-meta,
	.summary-panel,
	.template-panel-header,
	.section-card-topline,
	.actions {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
		align-items: start;
	}

	.review-meta,
	.section-heading,
	.component-list {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.eyebrow,
	.label {
		margin: 0;
		font-size: 0.76rem;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: #6b7c88;
	}

	h2,
	h3,
	p {
		margin: 0;
	}

	.lede,
	.small-copy {
		color: #625a50;
		line-height: 1.6;
	}

	.meta-pill,
	.score-pill,
	.order-pill,
	.role-pill,
	.component-list span {
		display: inline-flex;
		align-items: center;
		border-radius: 999px;
		padding: 0.35rem 0.7rem;
		font-size: 0.78rem;
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}

	.meta-pill,
	.score-pill,
	.order-pill,
	.role-pill {
		background: rgba(25, 45, 60, 0.08);
		color: #24343f;
	}

	.component-list span {
		background: rgba(29, 158, 117, 0.09);
		color: #0b6a52;
		font-size: 0.74rem;
	}

	.notice {
		margin: 0;
		border-radius: 1rem;
		padding: 0.9rem 1rem;
	}

	.notice-error {
		background: rgba(255, 242, 238, 0.94);
		color: #7d3524;
	}

	.notice-warn {
		background: rgba(255, 248, 225, 0.92);
		color: #7f5d13;
	}

	.summary-panel,
	.template-panel,
	.section-panel {
		display: grid;
		gap: 0.9rem;
		border: 0.5px solid rgba(36, 52, 63, 0.12);
		border-radius: 1.4rem;
		background: rgba(255, 255, 255, 0.84);
		padding: 1.15rem;
	}

	.summary-side {
		display: grid;
		justify-items: end;
		gap: 0.55rem;
		max-width: 24rem;
	}

	.template-grid,
	.section-list {
		display: grid;
		gap: 0.8rem;
	}

	.template-grid {
		grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
	}

	.template-option,
	.section-card {
		display: grid;
		gap: 0.8rem;
		border-radius: 1.1rem;
		border: 0.5px solid rgba(36, 52, 63, 0.1);
		background: linear-gradient(180deg, rgba(247, 245, 240, 0.92), rgba(255, 255, 255, 0.9));
		padding: 0.95rem;
		text-align: left;
	}

	.template-option {
		cursor: pointer;
	}

	.template-option-topline {
		display: flex;
		justify-content: space-between;
		gap: 0.5rem;
		align-items: center;
	}

	.template-option-topline span {
		color: #6b7c88;
		font-size: 0.8rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
	}

	.template-option p {
		color: #655c52;
		line-height: 1.55;
	}

	.template-selected {
		border-color: rgba(29, 158, 117, 0.52);
		background: linear-gradient(180deg, rgba(225, 245, 238, 0.88), rgba(255, 255, 255, 0.94));
	}

	.field {
		display: grid;
		gap: 0.45rem;
	}

	.field span {
		font-size: 0.86rem;
		font-weight: 600;
		color: #24343f;
	}

	input,
	textarea {
		border: 0.5px solid rgba(36, 52, 63, 0.12);
		border-radius: 0.9rem;
		padding: 0.72rem 0.85rem;
		font: inherit;
		background: #f7f4ee;
		color: #1d1b17;
	}

	textarea {
		resize: vertical;
	}

	.primary-button,
	.secondary-button {
		border: none;
		border-radius: 0.95rem;
		padding: 0.72rem 1.15rem;
		font: inherit;
		font-weight: 700;
		cursor: pointer;
	}

	.primary-button {
		background: #1d9e75;
		color: #e1f5ee;
	}

	.secondary-button {
		background: rgba(36, 67, 106, 0.08);
		color: #24436a;
	}

	.primary-button:disabled,
	.secondary-button:disabled,
	.template-option:disabled,
	input:disabled,
	textarea:disabled {
		cursor: not-allowed;
		opacity: 0.65;
	}

	@media (max-width: 720px) {
		.review-header,
		.summary-panel,
		.template-panel-header,
		.section-card-topline,
		.actions {
			flex-direction: column;
		}

		.summary-side {
			justify-items: start;
		}
	}
</style>

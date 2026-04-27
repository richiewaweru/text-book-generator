<script lang="ts">
	import { depthOptions, outcomeOptions, resourceTypeOptions, supportOptions } from '$lib/brief/config';
	import type {
		BriefValidationResult,
		BuilderWarning,
		TeacherBrief
	} from '$lib/types';

	interface Props {
		brief: Partial<TeacherBrief>;
		learnerSummary: string;
		validationResult: BriefValidationResult | null;
		warnings: BuilderWarning[];
		validating?: boolean;
		onValidate: () => void;
		onNotesInput: (value: string) => void;
	}

	let {
		brief,
		learnerSummary,
		validationResult,
		warnings,
		validating = false,
		onValidate,
		onNotesInput
	}: Props = $props();
</script>

<div class="review">
	<div class="summary-grid">
		<div>
			<span>Subject</span>
			<strong>{brief.subject ?? 'Not set'}</strong>
		</div>
		<div>
			<span>Topic</span>
			<strong>{brief.topic ?? 'Not set'}</strong>
		</div>
		<div>
			<span>Subtopic</span>
			<strong>{brief.subtopic ?? 'Not set'}</strong>
		</div>
		<div>
			<span>Learners</span>
			<strong>{learnerSummary || 'Not set'}</strong>
		</div>
		<div>
			<span>Outcome</span>
			<strong>
				{outcomeOptions.find((option) => option.value === brief.intended_outcome)?.label ?? 'Not set'}
			</strong>
		</div>
		<div>
			<span>Resource</span>
			<strong>
				{resourceTypeOptions.find((option) => option.value === brief.resource_type)?.label ?? 'Not set'}
			</strong>
		</div>
		<div>
			<span>Supports</span>
			<strong>
				{#if brief.supports?.length}
					{brief.supports
						.map((support) => supportOptions.find((option) => option.value === support)?.label ?? support)
						.join(', ')}
				{:else}
					No extra supports selected
				{/if}
			</strong>
		</div>
		<div>
			<span>Depth</span>
			<strong>{depthOptions.find((option) => option.value === brief.depth)?.label ?? 'Not set'}</strong>
		</div>
	</div>

	<label class="field">
		<span>Teacher notes</span>
		<textarea
			rows="3"
			value={brief.teacher_notes ?? ''}
			placeholder="Avoid long word problems. Keep reading simple. Use positive numbers only."
			oninput={(event) => onNotesInput((event.currentTarget as HTMLTextAreaElement).value)}
		></textarea>
	</label>

	<button type="button" class="primary" onclick={onValidate} disabled={validating}>
		{validating ? 'Checking brief...' : 'Validate brief'}
	</button>

	{#if validationResult}
		<div class:ready={validationResult.is_ready} class="validation-card">
			<strong>{validationResult.is_ready ? 'Ready for generation' : 'Needs edits before generation'}</strong>
		</div>
	{/if}

	{#if warnings.length > 0}
		<div class="alerts">
			{#each warnings as warning}
				<div class:blocking={warning.severity === 'blocking'} class="alert">
					<strong>{warning.severity === 'blocking' ? 'Blocker' : 'Warning'}</strong>
					<p>{warning.message}</p>
				</div>
			{/each}
		</div>
	{/if}

	{#if validationResult?.suggestions.length}
		<div class="suggestions">
			<strong>Suggestions</strong>
			<ul>
				{#each validationResult.suggestions as suggestion}
					<li>{suggestion.suggestion}</li>
				{/each}
			</ul>
		</div>
	{/if}
</div>

<style>
	.review {
		display: grid;
		gap: 1rem;
	}

	.summary-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
		gap: 0.85rem;
	}

	.summary-grid div,
	.validation-card,
	.alert,
	.suggestions {
		border: 1px solid rgba(36, 52, 63, 0.12);
		border-radius: 18px;
		background: white;
		padding: 0.9rem;
	}

	.summary-grid span {
		display: block;
		margin-bottom: 0.3rem;
		font-size: 0.78rem;
		font-weight: 700;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: #6b7c88;
	}

	.field {
		display: grid;
		gap: 0.45rem;
	}

	.field span {
		font-weight: 700;
	}

	textarea {
		border: 1px solid rgba(36, 52, 63, 0.14);
		border-radius: 16px;
		padding: 0.9rem 1rem;
		font: inherit;
		background: #fffdf9;
		resize: vertical;
	}

	.primary {
		justify-self: start;
		border: 0;
		border-radius: 999px;
		background: #1d9e75;
		color: white;
		padding: 0.8rem 1.1rem;
		font-weight: 700;
		cursor: pointer;
	}

	.validation-card.ready {
		border-color: rgba(29, 158, 117, 0.28);
		background: #eaf7f2;
		color: #085041;
	}

	.alerts {
		display: grid;
		gap: 0.7rem;
	}

	.alert.blocking {
		border-color: rgba(174, 73, 46, 0.2);
		background: #fff3ef;
	}

	.alert p,
	.suggestions ul {
		margin: 0.45rem 0 0 0;
		color: #655c52;
	}
</style>

<script lang="ts">
	import type { PlanningGenerationSpec } from '$lib/types';

	interface Props {
		plan: PlanningGenerationSpec;
		loading?: boolean;
		onBack: () => void;
		onCommit: () => void;
	}

	const COMPONENT_LABELS: Record<string, string> = {
		'hook-hero': 'Hook',
		'explanation-block': 'Explanation',
		'worked-example-card': 'Worked Example',
		'practice-stack': 'Practice',
		'definition-card': 'Definition',
		'glossary-strip': 'Glossary',
		'diagram-block': 'Diagram',
		'diagram-series': 'Diagram Series',
		'diagram-compare': 'Comparison Diagram',
		'what-next-bridge': 'What Next',
		'callout-block': 'Callout',
		'section-header': 'Section Header',
		'summary-block': 'Summary',
		'process-steps': 'Process Steps',
		'comparison-grid': 'Comparison Grid',
		'timeline-block': 'Timeline',
		'simulation-block': 'Simulation',
		'reflection-prompt': 'Reflection'
	};

	let { plan, loading = false, onBack, onCommit }: Props = $props();

	function labelForComponent(component: string): string {
		return COMPONENT_LABELS[component] ?? component.replaceAll('-', ' ');
	}
</script>

<section class="review-shell">
	<header class="review-header">
		<div>
			<p class="eyebrow">Plan Review</p>
			<h2>{plan.source_brief.subtopic}</h2>
			<p class="lede">{plan.lesson_rationale}</p>
		</div>
		<div class="meta">
			<span>{plan.source_brief.resource_type.replaceAll('_', ' ')}</span>
			<span>{plan.source_brief.depth}</span>
		</div>
	</header>

	{#if plan.warning}
		<p class="warning" role="status">{plan.warning}</p>
	{/if}

	<div class="section-grid">
		{#each plan.sections as section}
			<article class="section-card">
				<div class="section-head">
					<span class="section-order">Section {section.order}</span>
					<span class="section-role">{section.role}</span>
				</div>
				<h3>{section.title}</h3>
				<p>{section.objective ?? section.focus_note ?? section.rationale}</p>
				<div class="chip-row">
					{#each section.selected_components as component}
						<span class="chip">{labelForComponent(component)}</span>
					{/each}
				</div>
			</article>
		{/each}
	</div>

	<div class="actions">
		<button type="button" class="secondary" onclick={onBack} disabled={loading}>Back</button>
		<button type="button" class="primary" onclick={onCommit} disabled={loading}>
			{loading ? 'Starting generation...' : 'Generate'}
		</button>
	</div>
</section>

<style>
	.review-shell {
		display: grid;
		gap: 1rem;
	}

	.review-header,
	.section-head,
	.actions {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
		align-items: start;
	}

	.eyebrow {
		margin: 0 0 0.35rem 0;
		font-size: 0.76rem;
		font-weight: 700;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: #6b7c88;
	}

	h2,
	h3,
	p {
		margin: 0;
	}

	.lede {
		margin-top: 0.45rem;
		max-width: 62ch;
		color: #625a50;
		line-height: 1.6;
	}

	.meta,
	.chip-row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.meta span,
	.section-order,
	.section-role,
	.chip {
		border-radius: 999px;
		padding: 0.35rem 0.7rem;
		font-size: 0.76rem;
		font-weight: 700;
		background: #f1ece4;
		color: #4f5c65;
		text-transform: uppercase;
	}

	.warning {
		margin: 0;
		border-radius: 0.95rem;
		padding: 0.85rem 0.95rem;
		background: #fff8e4;
		color: #805d16;
	}

	.section-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
		gap: 1rem;
	}

	.section-card {
		display: grid;
		gap: 0.8rem;
		border-radius: 1rem;
		border: 1px solid rgba(36, 52, 63, 0.12);
		background: #fffdf9;
		padding: 1rem;
	}

	.section-card p {
		color: #625a50;
		line-height: 1.55;
	}

	.actions {
		justify-content: flex-end;
	}

	.primary,
	.secondary {
		border-radius: 999px;
		padding: 0.8rem 1.1rem;
		font-weight: 700;
		cursor: pointer;
	}

	.primary {
		border: 0;
		background: #1d9e75;
		color: white;
	}

	.secondary {
		border: 0;
		background: #f1ece4;
		color: #4f5c65;
	}

	@media (max-width: 720px) {
		.review-header,
		.section-head,
		.actions {
			flex-direction: column;
			align-items: stretch;
		}
	}
</style>

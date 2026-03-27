<script lang="ts">
	import { planDraft } from '$lib/stores/studio';
</script>

<section class="planning-shell" aria-live="polite">
	<div class="planning-header">
		<div>
			<p class="eyebrow">Planning</p>
			<h2>Streaming the lesson structure</h2>
			<p class="lede">
				The planner is choosing a template first, then laying down sections one by one so the
				latency stays visible.
			</p>
		</div>
		<div class="status-pill">Live planning</div>
	</div>

	{#if $planDraft.template_decision}
		<section class="template-panel">
			<p class="label">Selected template</p>
			<div class="template-row">
				<div>
					<h3>{$planDraft.template_decision.chosen_name}</h3>
					<p>{$planDraft.lesson_rationale || $planDraft.template_decision.rationale}</p>
				</div>
				<div class="fit-score">Fit {$planDraft.template_decision.fit_score.toFixed(2)}</div>
			</div>
			{#if $planDraft.warning}
				<p class="notice">{$planDraft.warning}</p>
			{/if}
		</section>
	{:else}
		<section class="template-panel template-panel-loading" aria-busy="true">
			<p class="label">Selected template</p>
			<div class="skeleton-line short"></div>
			<div class="skeleton-line"></div>
		</section>
	{/if}

	<section class="section-panel">
		<div class="section-panel-header">
			<p class="label">Sections arriving</p>
			<span>{$planDraft.sections.length} planned</span>
		</div>

		<div class="section-list">
			{#if $planDraft.sections.length}
				{#each $planDraft.sections as section}
					<article class="section-row" style={`--row-index:${section.order};`}>
						<div class="section-order">0{section.order}</div>
						<div class="section-copy">
							<div class="section-topline">
								<h3>{section.title}</h3>
								<span class="role-pill">{section.role}</span>
							</div>
							<p>{section.objective || section.rationale}</p>
						</div>
					</article>
				{/each}
			{:else}
				{#each Array.from({ length: 3 }) as _, index}
					<article class="section-row section-row-loading" aria-busy="true">
						<div class="section-order">0{index + 1}</div>
						<div class="section-copy">
							<div class="skeleton-line short"></div>
							<div class="skeleton-line"></div>
						</div>
					</article>
				{/each}
			{/if}
		</div>
	</section>
</section>

<style>
	.planning-shell {
		display: grid;
		gap: 1rem;
	}

	.planning-header,
	.template-row,
	.section-panel-header,
	.section-topline {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
		align-items: start;
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

	.lede {
		margin-top: 0.4rem;
		max-width: 58ch;
		color: #625a50;
		line-height: 1.6;
	}

	.status-pill,
	.fit-score,
	.role-pill {
		display: inline-flex;
		align-items: center;
		border-radius: 999px;
		padding: 0.35rem 0.7rem;
		font-size: 0.78rem;
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}

	.status-pill {
		background: rgba(29, 158, 117, 0.12);
		color: #0b6a52;
	}

	.fit-score,
	.role-pill {
		background: rgba(25, 45, 60, 0.08);
		color: #24343f;
	}

	.template-panel,
	.section-panel {
		display: grid;
		gap: 0.9rem;
		border: 0.5px solid rgba(36, 52, 63, 0.12);
		border-radius: 1.4rem;
		background: rgba(255, 255, 255, 0.84);
		padding: 1.15rem;
	}

	.template-panel-loading {
		min-height: 7rem;
	}

	.notice {
		border-radius: 1rem;
		background: rgba(255, 248, 225, 0.92);
		padding: 0.8rem 0.95rem;
		color: #7f5d13;
	}

	.section-list {
		display: grid;
		gap: 0.8rem;
	}

	.section-row {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0.9rem;
		border-radius: 1.1rem;
		background: linear-gradient(180deg, rgba(247, 245, 240, 0.92), rgba(255, 255, 255, 0.9));
		padding: 0.9rem;
		border: 0.5px solid rgba(36, 52, 63, 0.08);
		animation: row-in 220ms ease-out;
		animation-delay: calc(var(--row-index, 1) * 60ms);
		animation-fill-mode: both;
	}

	.section-row-loading {
		animation: none;
	}

	.section-order {
		display: grid;
		place-items: center;
		width: 2.4rem;
		height: 2.4rem;
		border-radius: 999px;
		background: rgba(29, 158, 117, 0.1);
		color: #0b6a52;
		font-size: 0.82rem;
		font-weight: 700;
	}

	.section-copy {
		display: grid;
		gap: 0.45rem;
	}

	.section-copy p {
		color: #655c52;
		line-height: 1.55;
	}

	.skeleton-line {
		height: 0.8rem;
		border-radius: 999px;
		background: linear-gradient(
			90deg,
			rgba(229, 224, 214, 0.7),
			rgba(247, 243, 236, 0.95),
			rgba(229, 224, 214, 0.7)
		);
		background-size: 200% 100%;
		animation: shimmer 1.25s linear infinite;
	}

	.skeleton-line.short {
		width: 52%;
	}

	@keyframes shimmer {
		from {
			background-position: 200% 0;
		}
		to {
			background-position: -200% 0;
		}
	}

	@keyframes row-in {
		from {
			opacity: 0;
			transform: translateY(8px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	@media (max-width: 720px) {
		.planning-header,
		.template-row,
		.section-panel-header,
		.section-topline {
			flex-direction: column;
		}
	}
</style>

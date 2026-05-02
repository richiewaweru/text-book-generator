<script lang="ts">
	import type { BuildMode } from '$lib/types';

	let {
		selected,
		onSelect
	}: {
		selected?: BuildMode;
		onSelect: (mode: BuildMode) => void;
	} = $props();
</script>

<div class="mode-grid">
	<button
		type="button"
		class="mode-card"
		class:selected={selected === 'single'}
		onclick={() => onSelect('single')}
	>
		<div class="mode-icon">O</div>
		<div class="mode-body">
			<strong class="mode-title">Single Lesson</strong>
			<p class="mode-desc">
				One focused resource tailored to your class with resource-level control.
			</p>
		</div>
	</button>

	<button
		type="button"
		class="mode-card"
		class:selected={selected === 'pack'}
		onclick={() => onSelect('pack')}
	>
		<div class="mode-icon">[]</div>
		<div class="mode-body">
			<strong class="mode-title">Learning Pack</strong>
			<p class="mode-desc">
				A coordinated set of resources sharing objective, vocabulary, and progression.
			</p>
		</div>
	</button>
</div>

<style>
	.mode-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
		gap: 0.85rem;
	}

	.mode-card {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0.8rem;
		text-align: left;
		border: 1px solid rgba(36, 52, 63, 0.12);
		border-radius: 18px;
		background: white;
		padding: 1rem;
		cursor: pointer;
	}

	.mode-card.selected {
		border-color: rgba(29, 158, 117, 0.28);
		background: #eaf7f2;
	}

	.mode-icon {
		width: 1.8rem;
		height: 1.8rem;
		border-radius: 999px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		background: rgba(36, 52, 63, 0.08);
		font-size: 0.75rem;
		font-weight: 700;
	}

	.mode-body {
		display: grid;
		gap: 0.3rem;
	}

	.mode-title {
		font-size: 0.96rem;
	}

	.mode-desc {
		margin: 0;
		color: #655c52;
		line-height: 1.5;
		font-size: 0.85rem;
	}
</style>

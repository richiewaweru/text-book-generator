<script lang="ts">
	import { resourceTypeOptions } from '$lib/brief/config';
	import type { TeacherBriefResourceType } from '$lib/types';

	interface Props {
		selected?: TeacherBriefResourceType;
		onSelect: (value: TeacherBriefResourceType) => void;
	}

	let { selected, onSelect }: Props = $props();
</script>

<div class="grid">
	{#each resourceTypeOptions as option}
		<button
			type="button"
			class:selected={selected === option.value}
			class="card"
			onclick={() => onSelect(option.value)}
		>
			<strong>{option.label}</strong>
			<span>{option.description}</span>
		</button>
	{/each}
</div>

<style>
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
		gap: 0.8rem;
	}

	.card {
		display: grid;
		gap: 0.4rem;
		text-align: left;
		border: 1px solid rgba(36, 52, 63, 0.12);
		border-radius: 18px;
		background: white;
		padding: 1rem;
		cursor: pointer;
	}

	.card.selected {
		border-color: rgba(29, 158, 117, 0.28);
		background: #eaf7f2;
	}

	.card span {
		color: #655c52;
		line-height: 1.5;
	}
</style>

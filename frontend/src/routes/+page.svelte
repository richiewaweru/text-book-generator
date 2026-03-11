<script lang="ts">
	import ProfileForm from '$lib/components/ProfileForm.svelte';
	import GenerationProgress from '$lib/components/GenerationProgress.svelte';
	import type { GenerationRequest, GenerationStatus } from '$lib/types';

	let status: GenerationStatus | null = $state(null);
	let generating = $state(false);

	async function handleGenerate(request: GenerationRequest) {
		generating = true;
		// TODO: Wire up to API client when backend is implemented
		console.log('Generation requested:', request);
		generating = false;
	}
</script>

<h1>Textbook Generation Agent</h1>
<p>Generate a personalized textbook tailored to your learning profile.</p>

<ProfileForm onsubmit={handleGenerate} disabled={generating} />

{#if status}
	<GenerationProgress {status} />
{/if}

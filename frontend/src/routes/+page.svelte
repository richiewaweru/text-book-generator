<script lang="ts">
	import ProfileForm from '$lib/components/ProfileForm.svelte';
	import GenerationProgress from '$lib/components/GenerationProgress.svelte';
	import { startGeneration, pollUntilDone } from '$lib/api/client';
	import type { GenerationRequest, GenerationStatus } from '$lib/types';
	import { goto } from '$app/navigation';

	let status: GenerationStatus | null = $state(null);
	let generating = $state(false);
	let errorMessage: string | null = $state(null);

	async function handleGenerate(request: GenerationRequest) {
		generating = true;
		errorMessage = null;
		status = null;

		try {
			const { generation_id } = await startGeneration(request);

			const finalStatus = await pollUntilDone(generation_id, (s) => {
				status = s;
			});

			if (finalStatus.status === 'completed' && finalStatus.result) {
				goto(`/textbook/${finalStatus.result.textbook_id}`);
			} else if (finalStatus.status === 'failed') {
				errorMessage = finalStatus.error ?? 'Generation failed unexpectedly.';
			}
		} catch (err) {
			errorMessage = err instanceof Error ? err.message : 'An unknown error occurred.';
		} finally {
			generating = false;
		}
	}
</script>

<h1>Textbook Generation Agent</h1>
<p>Generate a personalized textbook tailored to your learning profile.</p>

<ProfileForm onsubmit={handleGenerate} disabled={generating} />

{#if status}
	<GenerationProgress {status} />
{/if}

{#if errorMessage}
	<div class="error">
		<p><strong>Error:</strong> {errorMessage}</p>
	</div>
{/if}

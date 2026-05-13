<script lang="ts">
	import { fileToDataUri, validateRasterImageFile } from '$lib/builder/utils/media-utils';

	let {
		onReady
	}: {
		onReady: (payload: { dataUri: string; filename: string; mimeType: string }) => void;
	} = $props();

	let warning = $state<string | null>(null);

	async function onPick(e: Event): Promise<void> {
		const input = e.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		input.value = '';
		if (!file) return;
		const v = validateRasterImageFile(file);
		if (!v.ok) {
			warning = v.reason;
			return;
		}
		warning = null;
		try {
			const dataUri = await fileToDataUri(file);
			onReady({ dataUri, filename: file.name, mimeType: file.type });
		} catch {
			warning = 'Could not read the file.';
		}
	}
</script>

<div class="space-y-2">
	<label class="block text-xs font-medium text-slate-600" for="image-upload-input">Upload image</label>
	<input
		id="image-upload-input"
		type="file"
		accept="image/png,image/jpeg,image/webp,image/gif"
		class="block w-full text-sm text-slate-600 file:mr-3 file:rounded-md file:border file:border-slate-300 file:bg-white file:px-3 file:py-1.5 file:text-sm file:font-medium"
		onchange={onPick}
	/>
	{#if warning}
		<p class="text-xs text-amber-700">{warning}</p>
	{/if}
</div>

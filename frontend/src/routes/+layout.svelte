<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';

	let mounted = $state(false);

	onMount(() => {
		mounted = true;
		console.log('layout mounted');
	});
</script>

<p>DEBUG mounted: {String(mounted)}</p>
<p>LAYOUT ONLY</p>
<script lang="ts">
	import { goto } from '$app/navigation';
	import { fromStore } from 'svelte/store';
	import { resolveLandingRoute } from '$lib/auth/routing';
	import { authUser } from '$lib/stores/auth';

	const user = fromStore(authUser);

	$effect(() => {
		goto(resolveLandingRoute(user.current), { replaceState: true });
	});
</script>

<p>Redirecting...</p>

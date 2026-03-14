<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { fromStore } from 'svelte/store';
	import { fetchCurrentUser } from '$lib/api/auth';
	import { authInitialized, authIsAuthenticated, authUser, bootstrapAuth, logout } from '$lib/stores/auth';

	let { children } = $props();
	const initialized = fromStore(authInitialized);
	const user = fromStore(authUser);
	const authed = fromStore(authIsAuthenticated);

	onMount(() => {
		void bootstrapAuth(fetchCurrentUser);
	});

	$effect(() => {
		if (!initialized.current) return;
		const path = page.url.pathname;
		const isLogin = path.startsWith('/login');
		const isOnboarding = path.startsWith('/onboarding');

		if (!user.current) {
			if (!isLogin) {
				goto('/login', { replaceState: true });
			}
			return;
		}

		if (!user.current.has_profile && !isOnboarding) {
			goto('/onboarding', { replaceState: true });
		}
	});

	function handleLogout() {
		logout();
		goto('/login', { replaceState: true });
	}
</script>

<svelte:head>
	<title>Textbook Agent</title>
</svelte:head>

<header>
	<nav>
		<a href={authed.current ? '/dashboard' : '/'} class="brand">Textbook Agent</a>
		{#if authed.current && user.current}
			<div class="nav-right">
				{#if user.current.picture_url}
					<img src={user.current.picture_url} alt={user.current.name ?? ''} class="avatar" />
				{/if}
				<span class="user-name">{user.current.name ?? user.current.email}</span>
				<button onclick={handleLogout} class="logout-btn">Sign out</button>
			</div>
		{/if}
	</nav>
</header>

<main>
	{#if initialized.current}
		{@render children()}
	{:else}
		<p>Loading session...</p>
	{/if}
</main>

<style>
	:global(body) {
		margin: 0;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
		background: #111;
		color: #eee;
	}

	header {
		border-bottom: 1px solid #333;
		padding: 0.75rem 1.5rem;
	}

	nav {
		display: flex;
		align-items: center;
		justify-content: space-between;
		max-width: 1200px;
		margin: 0 auto;
	}

	.brand {
		font-weight: 700;
		font-size: 1.1rem;
		color: #eee;
		text-decoration: none;
	}

	.nav-right {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.avatar {
		width: 28px;
		height: 28px;
		border-radius: 50%;
	}

	.user-name {
		font-size: 0.9rem;
		color: #ccc;
	}

	.logout-btn {
		background: none;
		border: 1px solid #555;
		color: #ccc;
		padding: 0.25rem 0.75rem;
		border-radius: 4px;
		cursor: pointer;
		font-size: 0.8rem;
	}

	.logout-btn:hover {
		border-color: #888;
		color: #fff;
	}

	main {
		max-width: 1200px;
		margin: 0 auto;
		padding: 1.5rem;
	}
</style>

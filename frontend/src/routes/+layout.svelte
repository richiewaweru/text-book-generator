<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { initAuth, isAuthenticated, getUser, logout } from '$lib/stores/auth';

	let { children } = $props();
	let mounted = $state(false);

	const publicPaths = ['/login'];

	onMount(() => {
		initAuth();
		mounted = true;
	});

	$effect(() => {
		if (!mounted) return;
		const path = page.url.pathname;
		const isPublic = publicPaths.some((p) => path.startsWith(p));
		if (!isAuthenticated() && !isPublic) {
			goto('/login');
		}
	});

	function handleLogout() {
		logout();
		goto('/login');
	}

	const user = $derived(getUser());
	const authed = $derived(isAuthenticated());
</script>

<svelte:head>
	<title>Textbook Agent</title>
</svelte:head>

<header>
	<nav>
		<a href={authed ? '/dashboard' : '/'} class="brand">Textbook Agent</a>
		{#if authed && user}
			<div class="nav-right">
				{#if user.picture_url}
					<img src={user.picture_url} alt={user.name ?? ''} class="avatar" />
				{/if}
				<span class="user-name">{user.name ?? user.email}</span>
				<button onclick={handleLogout} class="logout-btn">Sign out</button>
			</div>
		{/if}
	</nav>
</header>

<main>
	{#if mounted}
		{@render children()}
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

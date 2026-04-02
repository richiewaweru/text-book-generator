<script lang="ts">
	import '../app.css';
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
	const isPrintTextbookRoute = $derived(
		page.url.pathname.startsWith('/textbook/') && page.url.searchParams.get('print') === 'true'
	);

	onMount(() => {
		void bootstrapAuth(fetchCurrentUser);
	});

	$effect(() => {
		if (!initialized.current) return;
		const path = page.url.pathname;
		const isLogin = path.startsWith('/login');
		const isOnboarding = path.startsWith('/onboarding');
		if (isPrintTextbookRoute) {
			return;
		}

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

{#if !isPrintTextbookRoute}
	<header>
		<nav>
			<div class="nav-left">
				<a href={authed.current ? '/dashboard' : '/'} class="brand">Textbook Agent</a>
				{#if authed.current && user.current}
					<div class="nav-links">
						<a href="/dashboard" class="nav-link">Dashboard</a>
						<a href="/studio" class="nav-link">Studio</a>
					</div>
				{/if}
			</div>
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
{/if}

<main>
	{#if initialized.current || isPrintTextbookRoute}
		{@render children()}
	{:else}
		<p>Loading session...</p>
	{/if}
</main>

<style>
	:global(body) {
		margin: 0;
		font-family:
			'Iowan Old Style', 'Palatino Linotype', 'Book Antiqua', Palatino, Georgia, serif;
		background:
			radial-gradient(circle at top, rgba(214, 196, 160, 0.22), transparent 32%),
			linear-gradient(180deg, #f4efe4 0%, #ece3d1 52%, #e4d7c0 100%);
		color: #1e1b16;
	}

	header {
		border-bottom: 1px solid rgba(61, 47, 26, 0.15);
		padding: 0.75rem 1.5rem;
		backdrop-filter: blur(12px);
		background: rgba(250, 245, 235, 0.82);
	}

	nav {
		display: flex;
		align-items: center;
		justify-content: space-between;
		max-width: 1200px;
		margin: 0 auto;
	}

	.nav-left,
	.nav-links,
	.nav-right {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.brand {
		font-weight: 700;
		font-size: 1.1rem;
		color: #1f2b34;
		text-decoration: none;
	}

	.nav-link {
		color: #5f574d;
		text-decoration: none;
		font-size: 0.92rem;
	}

	.avatar {
		width: 28px;
		height: 28px;
		border-radius: 50%;
	}

	.user-name {
		font-size: 0.9rem;
		color: #5f574d;
	}

	.logout-btn {
		background: rgba(31, 43, 52, 0.05);
		border: 1px solid rgba(31, 43, 52, 0.15);
		color: #24343f;
		padding: 0.25rem 0.75rem;
		border-radius: 999px;
		cursor: pointer;
		font-size: 0.8rem;
	}

	.logout-btn:hover {
		border-color: rgba(31, 43, 52, 0.35);
		color: #111;
	}

	main {
		max-width: 1200px;
		margin: 0 auto;
		padding: 1.5rem;
	}

	@media (max-width: 720px) {
		nav,
		.nav-left,
		.nav-links,
		.nav-right {
			flex-wrap: wrap;
		}
	}
</style>

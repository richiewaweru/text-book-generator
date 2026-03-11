<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { exchangeGoogleToken } from '$lib/api/auth';
	import { setAuth, isAuthenticated } from '$lib/stores/auth';

	let errorMessage: string | null = $state(null);
	let loading = $state(false);

	onMount(() => {
		if (isAuthenticated()) {
			goto('/dashboard');
			return;
		}

		const script = document.createElement('script');
		script.src = 'https://accounts.google.com/gsi/client';
		script.async = true;
		script.defer = true;
		script.onload = () => {
			(window as any).google.accounts.id.initialize({
				client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID || '',
				callback: handleCredentialResponse
			});
			(window as any).google.accounts.id.renderButton(
				document.getElementById('google-signin-btn'),
				{
					theme: 'outline',
					size: 'large',
					width: 320,
					text: 'signin_with'
				}
			);
		};
		document.head.appendChild(script);
	});

	async function handleCredentialResponse(response: { credential: string }) {
		loading = true;
		errorMessage = null;
		try {
			const authResponse = await exchangeGoogleToken(response.credential);
			setAuth(authResponse);
			if (authResponse.user.has_profile) {
				goto('/dashboard');
			} else {
				goto('/onboarding');
			}
		} catch (err) {
			errorMessage = err instanceof Error ? err.message : 'Authentication failed.';
		} finally {
			loading = false;
		}
	}
</script>

<div class="login-container">
	<div class="login-card">
		<h1>Textbook Agent</h1>
		<p>Sign in to create personalized textbooks tailored to your learning profile.</p>

		<div id="google-signin-btn" class="google-btn-wrapper"></div>

		{#if loading}
			<p class="loading">Signing in...</p>
		{/if}

		{#if errorMessage}
			<p class="error">{errorMessage}</p>
		{/if}
	</div>
</div>

<style>
	.login-container {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 80vh;
	}

	.login-card {
		text-align: center;
		max-width: 400px;
		padding: 2.5rem;
		border: 1px solid #333;
		border-radius: 12px;
		background: #1a1a1a;
	}

	h1 {
		margin-bottom: 0.5rem;
		font-size: 1.75rem;
	}

	p {
		color: #aaa;
		margin-bottom: 1.5rem;
	}

	.google-btn-wrapper {
		display: flex;
		justify-content: center;
		margin: 1.5rem 0;
	}

	.loading {
		color: #6d9eeb;
	}

	.error {
		color: #e57373;
	}
</style>

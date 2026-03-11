<script lang="ts">
	let { children } = $props();
</script>

<svelte:head>
	<title>Textbook Agent</title>
</svelte:head>

<header>
	<nav>
		<a href="/">Textbook Agent</a>
	</nav>
</header>

<main>
	{@render children()}
</main>

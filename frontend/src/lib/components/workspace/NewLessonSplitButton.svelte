<script lang="ts">
</script>

<div class="split-button">
	<a class="primary" href="/units">+ New lesson</a>
</div>

<style>
	.split-button {
		position: relative;
		display: inline-flex;
		flex: 0 0 auto;
	}

	.primary {
		border: 1px solid #1c5d45;
		background: #1c5d45;
		color: #fff;
		font: 600 13px Inter, sans-serif;
	}

	.primary {
		border-radius: 7px 0 0 7px;
		padding: 9px 13px;
		text-decoration: none;
	}

	.primary:hover {
		background: #174f3b;
	}

	.primary:focus-visible {
		position: relative;
		z-index: 1;
		outline: 2px solid #1c5d45;
		outline-offset: 3px;
	}

	@media (prefers-reduced-motion: reduce) {
		.primary {
			transition: none;
		}
	}

	@media (max-width: 640px) {
		.split-button {
			width: 100%;
		}

		.primary {
			flex: 1;
			text-align: center;
		}
	}
</style>

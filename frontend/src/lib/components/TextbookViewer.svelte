<script lang="ts">
	import { onDestroy } from 'svelte';

	interface Props {
		html: string;
	}

	let { html }: Props = $props();

	let iframeEl: HTMLIFrameElement | null = $state(null);
	let frameHeight = $state(720);
	let cleanup: (() => void) | null = null;

	function teardownObservers() {
		cleanup?.();
		cleanup = null;
	}

	function syncFrameHeight() {
		const frameDoc = iframeEl?.contentDocument;
		if (!frameDoc) {
			return;
		}

		const nextHeight = Math.max(
			frameDoc.documentElement?.scrollHeight ?? 0,
			frameDoc.body?.scrollHeight ?? 0,
			720
		);
		frameHeight = nextHeight;
	}

	function handleLoad() {
		teardownObservers();
		syncFrameHeight();

		const frameDoc = iframeEl?.contentDocument;
		if (!frameDoc?.documentElement) {
			return;
		}

		const mutationObserver = new MutationObserver(syncFrameHeight);
		mutationObserver.observe(frameDoc.documentElement, {
			childList: true,
			subtree: true,
			attributes: true,
			characterData: true
		});

		const resizeObserver = new ResizeObserver(() => {
			syncFrameHeight();
		});
		resizeObserver.observe(frameDoc.documentElement);
		if (frameDoc.body) {
			resizeObserver.observe(frameDoc.body);
		}

		const timers = [
			window.setTimeout(syncFrameHeight, 150),
			window.setTimeout(syncFrameHeight, 800),
			window.setTimeout(syncFrameHeight, 1800)
		];

		cleanup = () => {
			mutationObserver.disconnect();
			resizeObserver.disconnect();
			for (const timer of timers) {
				window.clearTimeout(timer);
			}
		};
	}

	$effect(() => {
		html;
		teardownObservers();
		frameHeight = 720;
	});

	onDestroy(() => {
		teardownObservers();
	});
</script>

<div class="textbook-viewer">
	<iframe
		bind:this={iframeEl}
		class="textbook-frame"
		title="Generated textbook"
		srcdoc={html}
		onload={handleLoad}
		style={`height:${frameHeight}px`}
	></iframe>
</div>

<style>
	.textbook-viewer {
		width: 100%;
	}

	.textbook-frame {
		display: block;
		width: 100%;
		border: 0;
		border-radius: 16px;
		background: transparent;
	}
</style>

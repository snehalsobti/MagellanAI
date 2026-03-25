<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import AppBanner from '$lib/components/AppBanner.svelte';
	import { page } from '$app/stores';
	import { theme } from '$lib/stores/theme';
	import { browser } from '$app/environment';
	import '../app.css';

	let { children } = $props();
	const hideBanner = $derived(['/signin', '/options'].includes($page.url.pathname));

	// Apply saved theme on SSR hydration
	$effect(() => {
		if (browser) {
			document.documentElement.setAttribute('data-theme', $theme);
		}
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{#if !hideBanner}
	<AppBanner />
{/if}

{@render children()}

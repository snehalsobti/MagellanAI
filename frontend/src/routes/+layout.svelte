<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import AppBanner from '$lib/components/AppBanner.svelte';
	import { page } from '$app/stores';
	import '../app.css';

	let { children } = $props();
	const hideBanner = $derived(['/signin', '/options'].includes($page.url.pathname));
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{#if !hideBanner}
	<AppBanner />
{/if}

{@render children()}

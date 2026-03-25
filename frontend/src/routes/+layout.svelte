<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import AppBanner from '$lib/components/AppBanner.svelte';
	import { page } from '$app/stores';
	import { theme } from '$lib/stores/theme';
	import { browser } from '$app/environment';
	import { invalidate } from '$app/navigation';
	import { onMount } from 'svelte';
	import { supabase } from '$lib/auth';
	import '../app.css';

	let { children, data } = $props();
	const hideBanner = $derived(['/signin', '/options'].includes($page.url.pathname));

	// Apply saved theme on SSR hydration.
	$effect(() => {
		if (browser) {
			document.documentElement.setAttribute('data-theme', $theme);
		}
	});

	// Subscribe to Supabase auth state changes so the server-side session stays
	// in sync when tokens refresh or the user signs out in another tab.
	onMount(() => {
		if (!supabase) return;
		const {
			data: { subscription }
		} = supabase.auth.onAuthStateChange((_event, session) => {
			if (session?.expires_at !== data.session?.expires_at) {
				invalidate('supabase:auth');
			}
		});
		return () => subscription.unsubscribe();
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{#if !hideBanner}
	<AppBanner />
{/if}

{@render children()}

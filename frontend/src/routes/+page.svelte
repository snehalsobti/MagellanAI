<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		goto('/signin');
	});
</script>

<svelte:head>
	<title>MagellanAI</title>
</svelte:head>

<main class="redirect-page">
	<p>Redirecting...</p>
</main>

<style>
	.redirect-page { padding: 24px; color: var(--text-muted); }
</style>

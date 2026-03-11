<script lang="ts">
	import { goto } from '$app/navigation';
	import { getAuthMode } from '$lib/auth';
	import { onMount } from 'svelte';

	const cards = [
		{
			title: 'View the requirements that must be satisfied by a course profile',
			desc: 'Program rules, CEAB minimums, and CE/EE designation table.',
			path: '/requirements'
		},
		{
			title: 'Generate a new course profile',
			desc: 'Provide interests and get a validated personalized semester plan.',
			path: '/generate'
		},
		{
			title: 'View course list',
			desc: 'Search and filter the full course catalog by key attributes.',
			path: '/courses'
		}
	];

	onMount(() => {
		if (!getAuthMode()) goto('/signin');
	});
</script>

<main class="options-page">
	<h1>Choose what you want to do</h1>
	<div class="card-grid">
		{#each cards as card}
			<button type="button" class="option-card" on:click={() => goto(card.path)}>
				<h2>{card.title}</h2>
				<p>{card.desc}</p>
			</button>
		{/each}
	</div>
</main>

<style>
	.options-page { max-width: 1100px; margin: 0 auto; padding: 36px 18px; }
	h1 { margin: 0 0 16px; font-size: 1.7rem; }
	.card-grid { display: grid; gap: 14px; grid-template-columns: repeat(3, minmax(0, 1fr)); }
	.option-card {
		text-align: left;
		border: 1px solid var(--border);
		border-radius: 16px;
		padding: 20px;
		background: linear-gradient(145deg, #ffffff, #f5f8ff);
		box-shadow: var(--shadow-sm);
		cursor: pointer;
		transition: transform .15s ease, box-shadow .15s ease;
	}
	.option-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
	h2 { margin: 0 0 10px; font-size: 1rem; line-height: 1.4; }
	p { margin: 0; color: var(--text-muted); font-size: .88rem; line-height: 1.45; }
	@media (max-width: 980px){ .card-grid { grid-template-columns: 1fr; } }
</style>

<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { signOut } from '$lib/auth';

	const links = [
		{ href: '/requirements', label: 'Requirements' },
		{ href: '/generate', label: 'Generate Profile' },
		{ href: '/courses', label: 'Course List' },
		{ href: '/options', label: 'Options' }
	];

	function handleSignOut() {
		signOut();
		goto('/signin');
	}
</script>

<header class="banner">
	<button type="button" class="brand" onclick={() => goto('/options')}>
		<h1>MagellanAI</h1>
	</button>
	<nav>
		{#each links as link}
			<a href={link.href} class:active={$page.url.pathname === link.href}>{link.label}</a>
		{/each}
		<button type="button" class="signout" onclick={handleSignOut}>Sign out</button>
	</nav>
</header>

<style>
	.banner {
		position: sticky;
		top: 0;
		z-index: 50;
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 12px 18px;
		background: rgba(255, 255, 255, 0.9);
		backdrop-filter: blur(10px);
		border-bottom: 1px solid var(--border);
	}

	.brand {
		cursor: pointer;
		border: 0;
		background: transparent;
		padding: 0;
		color: inherit;
	}
	.brand h1 {
		margin: 0;
		font-size: 1.15rem;
	}

	nav {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-wrap: wrap;
		justify-content: flex-end;
	}

	a,
	.signout {
		text-decoration: none;
		border: 1px solid var(--border);
		background: #fff;
		color: var(--text);
		padding: 7px 10px;
		border-radius: 999px;
		font-size: 0.78rem;
		cursor: pointer;
	}

	a.active {
		background: #eaf2ff;
		border-color: #c8dcff;
		color: #1d4ed8;
	}

	.signout {
		background: #fee2e2;
		border-color: #fecaca;
		color: #991b1b;
	}
</style>

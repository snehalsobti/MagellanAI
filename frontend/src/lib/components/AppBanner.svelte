<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { signOut } from '$lib/auth';
	import { theme } from '$lib/stores/theme';
	import logo from '$lib/assets/magellanai_logo.png';

	const links = [
		{ href: '/requirements', label: 'Requirements' },
		{ href: '/generate',     label: 'Generate Profile' },
		{ href: '/courses',      label: 'Course Catalog' },
		{ href: '/options',      label: 'Navigation Hub' }
	];

	function handleSignOut() {
		signOut();
		goto('/signin');
	}
</script>

<header class="banner">
	<!-- Brand mark -->
	<button type="button" class="brand" onclick={() => goto('/options')} aria-label="Go to Navigation Hub">
		<img src={logo} alt="MagellanAI compass logo" class="brand-logo" />
		<span class="brand-name">MagellanAI</span>
	</button>

	<!-- Navigation -->
	<nav aria-label="Main navigation">
		{#each links as link}
			<a
				href={link.href}
				class="nav-link"
				class:active={$page.url.pathname === link.href}
				aria-current={$page.url.pathname === link.href ? 'page' : undefined}
			>
				{link.label}
			</a>
		{/each}

		<!-- Dark/Light toggle -->
		<button
			type="button"
			class="theme-toggle"
			onclick={() => theme.toggle()}
			aria-label={$theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
			title={$theme === 'dark' ? 'Switch to light mode (parchment)' : 'Switch to dark mode (ocean)'}
		>
			{#if $theme === 'dark'}
				<!-- Sun icon -->
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<circle cx="12" cy="12" r="4"/>
					<line x1="12" y1="2" x2="12" y2="6"/>
					<line x1="12" y1="18" x2="12" y2="22"/>
					<line x1="4.22" y1="4.22" x2="7.05" y2="7.05"/>
					<line x1="16.95" y1="16.95" x2="19.78" y2="19.78"/>
					<line x1="2" y1="12" x2="6" y2="12"/>
					<line x1="18" y1="12" x2="22" y2="12"/>
					<line x1="4.22" y1="19.78" x2="7.05" y2="16.95"/>
					<line x1="16.95" y1="7.05" x2="19.78" y2="4.22"/>
				</svg>
			{:else}
				<!-- Moon icon -->
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
				</svg>
			{/if}
		</button>

		<!-- Sign out -->
		<button type="button" class="signout-btn" onclick={handleSignOut} aria-label="Sign out">
			Sign out
		</button>
	</nav>
</header>

<style>
	.banner {
		position: sticky;
		top: 0;
		z-index: 100;
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 10px 20px;
		background: var(--surface);
		border-bottom: 1px solid var(--border);
		box-shadow: var(--shadow-sm);
		gap: 12px;
		/* Subtle top gold line */
		border-top: 2px solid var(--gold-dim);
	}

	/* Gold accent line at very top */
	.banner::before {
		content: '';
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 2px;
		background: linear-gradient(90deg, transparent, var(--gold), var(--ocean-light), var(--gold), transparent);
		opacity: 0.6;
	}

	/* ── Brand ──────────────────────────────────────────────────────────────── */
	.brand {
		display: flex;
		align-items: center;
		gap: 10px;
		border: none;
		background: transparent;
		padding: 4px 0;
		cursor: pointer;
		flex-shrink: 0;
		transition: opacity 0.18s ease;
	}
	.brand:hover { opacity: 0.85; }

	.brand-logo {
		width: 75px;
		height: 75px;
		object-fit: contain;
		filter: drop-shadow(0 0 6px rgba(201, 168, 76, 0.3));
		transition: filter 0.3s ease;
	}
	.brand:hover .brand-logo {
		filter: drop-shadow(0 0 10px rgba(201, 168, 76, 0.55));
	}

	.brand-name {
		font-family: 'Cinzel', serif;
		font-size: 1.05rem;
		font-weight: 600;
		letter-spacing: 0.08em;
		color: var(--gold);
		text-shadow: 0 0 16px rgba(201, 168, 76, 0.35);
		white-space: nowrap;
	}

	/* ── Nav ────────────────────────────────────────────────────────────────── */
	nav {
		display: flex;
		align-items: center;
		gap: 6px;
		flex-wrap: wrap;
		justify-content: flex-end;
	}

	.nav-link {
		text-decoration: none;
		color: var(--text-muted);
		padding: 6px 12px;
		border-radius: 999px;
		font-size: 0.78rem;
		font-weight: 500;
		letter-spacing: 0.02em;
		border: 1px solid transparent;
		transition: color 0.18s, border-color 0.18s, background 0.18s;
		white-space: nowrap;
		cursor: pointer;
	}
	.nav-link:hover {
		color: var(--text);
		border-color: var(--border);
		background: var(--surface-hover);
	}
	.nav-link.active {
		color: var(--gold);
		border-color: var(--gold-dim);
		background: rgba(201, 168, 76, 0.08);
		font-weight: 600;
	}

	/* ── Theme Toggle ───────────────────────────────────────────────────────── */
	.theme-toggle {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 34px;
		height: 34px;
		border-radius: 50%;
		border: 1px solid var(--border);
		background: var(--surface-raised);
		color: var(--text-muted);
		padding: 0;
		cursor: pointer;
		transition: all 0.2s ease;
		flex-shrink: 0;
	}
	.theme-toggle:hover {
		border-color: var(--gold-dim);
		color: var(--gold);
		background: rgba(201, 168, 76, 0.08);
		box-shadow: var(--glow-gold);
	}

	/* ── Sign Out ───────────────────────────────────────────────────────────── */
	.signout-btn {
		padding: 6px 12px;
		border-radius: 999px;
		border: 1px solid var(--compass-red);
		background: rgba(192, 57, 43, 0.08);
		color: var(--compass-red);
		font-size: 0.78rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.18s ease;
		white-space: nowrap;
	}
	.signout-btn:hover {
		background: rgba(192, 57, 43, 0.18);
		color: var(--text);
	}

	/* ── Responsive ──────────────────────────────────────────────────────────── */
	@media (max-width: 768px) {
		.banner {
			padding: 8px 14px;
			flex-wrap: wrap;
		}
		.nav-link {
			font-size: 0.72rem;
			padding: 5px 8px;
		}
	}

	@media (max-width: 480px) {
		.brand-name { display: none; }
	}
</style>

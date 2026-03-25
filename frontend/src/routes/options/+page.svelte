<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { signOut } from '$lib/auth';
	import { theme } from '$lib/stores/theme';
	import logo from '$lib/assets/magellanai_logo.png';
	// User info from server-side session (set by +layout.server.ts).
	const user = $derived($page.data.user);
	const isGuest = $derived(user?.is_anonymous === true);
	const displayName = $derived(
		isGuest
			? 'Guest'
			: user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'User'
	);

	const destinations = [
		{
			icon: '📜',
			heading: 'Requirements & Regulations',
			subheading: 'Program Charts',
			desc: 'Study the admiralty rules — program requirements, CEAB minimums, and CE/EE designation pathways.',
			path: '/requirements',
			accent: 'gold'
		},
		{
			icon: '🧭',
			heading: 'Generate Course Profile',
			subheading: 'Plot Your Course',
			desc: 'Provide your academic interests and let MagellanAI chart a complete, constraint-verified semester plan.',
			path: '/generate',
			accent: 'ocean'
		},
		{
			icon: '⚓',
			heading: 'Course Catalog',
			subheading: "Ship's Manifest",
			desc: 'Search and filter the full course catalog by area, type, CEAB attributes, and more.',
			path: '/courses',
			accent: 'muted'
		}
	];

	async function handleSignOut() {
		await signOut();
		goto('/signin');
	}
</script>

<svelte:head>
	<title>MagellanAI — Navigation Hub</title>
</svelte:head>

<main class="page">
	<!-- Header section -->
	<header class="page-header">
		<div class="header-brand">
			<img src={logo} alt="MagellanAI" class="header-logo" />
			<div class="header-text">
				<h1 class="page-title">Navigation Hub</h1>
				<p class="page-subtitle">Choose your heading, navigator</p>
			</div>
		</div>
		<div class="header-actions">
			{#if user}
				<span class="user-badge" title={isGuest ? 'Guest session' : user.email}>
					{#if isGuest}👤{:else}✦{/if}
					{displayName}
				</span>
			{/if}
			<button type="button" class="theme-toggle" onclick={() => theme.toggle()} aria-label="Toggle theme">
				{#if $theme === 'dark'}☀{:else}🌙{/if}
			</button>
			<button type="button" class="btn-signout" onclick={handleSignOut}>Sign out</button>
		</div>
	</header>

	<!-- Decorative latitude line -->
	<div class="latitude-line" aria-hidden="true">
		<span class="lat-label">43° N</span>
		<div class="lat-rule"></div>
	</div>

	<!-- Destination cards -->
	<div class="card-grid">
		{#each destinations as dest, i}
			<button
				type="button"
				class="dest-card accent-{dest.accent}"
				onclick={() => goto(dest.path)}
				style="animation-delay: {i * 0.1}s"
			>
				<!-- Card header with icon -->
				<div class="dest-icon-wrap">
					<span class="dest-icon" aria-hidden="true">{dest.icon}</span>
				</div>

				<!-- Card content -->
				<div class="dest-content">
					<div class="dest-subheading">{dest.subheading}</div>
					<h2 class="dest-heading">{dest.heading}</h2>
					<p class="dest-desc">{dest.desc}</p>
				</div>

				<!-- Hover arrow indicator -->
				<div class="dest-arrow" aria-hidden="true">
					<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M5 12h14M12 5l7 7-7 7"/>
					</svg>
				</div>

				<!-- Corner compass mark -->
				<div class="card-compass" aria-hidden="true">✦</div>
			</button>
		{/each}
	</div>

	<!-- Footer coordinates -->
	<footer class="page-footer">
		<span class="coord-text">43°39′N 79°23′W</span>
		<span class="separator" aria-hidden="true">·</span>
		<span class="coord-text">University of Toronto — ECE</span>
	</footer>
</main>

<style>
	/* ── Page layout ─────────────────────────────────────────────────────────── */
	.page {
		max-width: 1100px;
		margin: 0 auto;
		padding: 36px 24px 60px;
		display: grid;
		gap: 32px;
	}

	/* ── Page header ─────────────────────────────────────────────────────────── */
	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		flex-wrap: wrap;
		animation: fade-in 0.5s ease;
	}

	.header-brand {
		display: flex;
		align-items: center;
		gap: 14px;
	}

	.header-logo {
		width: 130px;
		height: 130px;
		object-fit: contain;
		filter: drop-shadow(0 0 10px rgba(201, 168, 76, 0.3));
	}

	.header-text { display: flex; flex-direction: column; gap: 2px; }

	.page-title {
		font-family: 'Cinzel', serif;
		font-size: 1.6rem;
		font-weight: 700;
		color: var(--gold);
		letter-spacing: 0.08em;
		margin: 0;
	}

	.page-subtitle {
		font-size: 0.8rem;
		color: var(--text-muted);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		margin: 0;
	}

	.header-actions {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.theme-toggle {
		width: 36px;
		height: 36px;
		border-radius: 50%;
		border: 1px solid var(--border);
		background: var(--surface-raised);
		color: var(--text-muted);
		font-size: 0.9rem;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		transition: all 0.2s ease;
	}
	.theme-toggle:hover {
		border-color: var(--gold-dim);
		color: var(--gold);
		box-shadow: var(--glow-gold);
	}

	.user-badge {
		font-size: 0.75rem;
		color: var(--text-muted);
		padding: 5px 10px;
		border-radius: 999px;
		border: 1px solid var(--border);
		background: var(--surface-raised);
		white-space: nowrap;
		max-width: 160px;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.btn-signout {
		padding: 7px 14px;
		border-radius: 999px;
		border: 1px solid var(--compass-red);
		background: rgba(192, 57, 43, 0.08);
		color: var(--compass-red);
		font-size: 0.78rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.18s ease;
	}
	.btn-signout:hover {
		background: rgba(192, 57, 43, 0.18);
	}

	/* ── Latitude decorative line ─────────────────────────────────────────────── */
	.latitude-line {
		display: flex;
		align-items: center;
		gap: 12px;
		opacity: 0.4;
	}
	.lat-label {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.68rem;
		letter-spacing: 0.1em;
		color: var(--gold);
		white-space: nowrap;
	}
	.lat-rule {
		flex: 1;
		height: 1px;
		background: linear-gradient(90deg, var(--gold-dim), transparent);
	}

	/* ── Destination card grid ───────────────────────────────────────────────── */
	.card-grid {
		display: grid;
		gap: 18px;
		grid-template-columns: repeat(3, minmax(0, 1fr));
	}

	/* ── Individual destination card ─────────────────────────────────────────── */
	.dest-card {
		position: relative;
		text-align: left;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 18px;
		padding: 28px 24px 24px;
		cursor: pointer;
		transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease, background 0.2s ease;
		display: flex;
		flex-direction: column;
		gap: 14px;
		overflow: hidden;
		animation: fade-in 0.6s ease both;
	}

	/* Top accent bar per card type */
	.dest-card::before {
		content: '';
		position: absolute;
		top: 0; left: 0; right: 0;
		height: 2px;
		border-radius: 18px 18px 0 0;
		opacity: 0.6;
		transition: opacity 0.2s ease;
	}

	.dest-card:hover {
		transform: translateY(-4px);
		box-shadow: var(--shadow-md);
	}

	/* Accent colour variants */
	.dest-card.accent-gold::before { background: linear-gradient(90deg, var(--gold), transparent); }
	.dest-card.accent-ocean::before { background: linear-gradient(90deg, var(--ocean-light), transparent); }
	.dest-card.accent-muted::before { background: linear-gradient(90deg, var(--text-faint), transparent); }

	.dest-card.accent-gold:hover  { border-color: var(--gold-dim); box-shadow: var(--shadow-md), var(--glow-gold); }
	.dest-card.accent-ocean:hover { border-color: var(--ocean); box-shadow: var(--shadow-md), var(--glow-ocean); }
	.dest-card.accent-muted:hover { border-color: var(--border); box-shadow: var(--shadow-md); }

	/* ── Card icon ───────────────────────────────────────────────────────────── */
	.dest-icon-wrap {
		width: 44px;
		height: 44px;
		border-radius: 12px;
		background: var(--surface-raised);
		border: 1px solid var(--border);
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s ease;
	}
	.dest-card:hover .dest-icon-wrap {
		background: var(--surface-hover);
	}
	.dest-icon { font-size: 1.3rem; line-height: 1; }

	/* ── Card text ───────────────────────────────────────────────────────────── */
	.dest-content { flex: 1; }

	.dest-subheading {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.64rem;
		letter-spacing: 0.18em;
		text-transform: uppercase;
		color: var(--text-faint);
		margin-bottom: 6px;
	}

	.dest-heading {
		font-family: 'Cinzel', serif;
		font-size: 1.05rem;
		font-weight: 600;
		letter-spacing: 0.04em;
		color: var(--text);
		margin: 0 0 10px;
	}

	.dest-desc {
		font-size: 0.85rem;
		color: var(--text-muted);
		line-height: 1.55;
		margin: 0;
	}

	/* ── Arrow indicator ─────────────────────────────────────────────────────── */
	.dest-arrow {
		color: var(--text-faint);
		display: flex;
		align-self: flex-end;
		opacity: 0;
		transform: translateX(-8px);
		transition: opacity 0.2s ease, transform 0.2s ease, color 0.2s ease;
	}
	.dest-card:hover .dest-arrow {
		opacity: 1;
		transform: translateX(0);
	}
	.dest-card.accent-gold:hover  .dest-arrow { color: var(--gold); }
	.dest-card.accent-ocean:hover .dest-arrow { color: var(--ocean-light); }
	.dest-card.accent-muted:hover .dest-arrow { color: var(--text-muted); }

	/* ── Corner compass mark ─────────────────────────────────────────────────── */
	.card-compass {
		position: absolute;
		bottom: 14px;
		right: 16px;
		font-size: 0.65rem;
		color: var(--gold-dim);
		opacity: 0.25;
		transition: opacity 0.2s ease;
	}
	.dest-card:hover .card-compass { opacity: 0.5; }

	/* ── Footer ──────────────────────────────────────────────────────────────── */
	.page-footer {
		display: flex;
		align-items: center;
		gap: 8px;
		justify-content: center;
		opacity: 0.75;
	}
	.coord-text {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.68rem;
		letter-spacing: 0.1em;
		color: var(--gold);
	}
	.separator { color: var(--gold); }

	/* ── Responsive ──────────────────────────────────────────────────────────── */
	@media (max-width: 900px) {
		.card-grid { grid-template-columns: 1fr; }
	}
	@media (max-width: 600px) {
		.page { padding: 24px 16px 40px; }
		.page-title { font-size: 1.3rem; }
	}
</style>

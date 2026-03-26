<script lang="ts">
	import { goto } from '$app/navigation';
	import { signInWithGoogle, signInAnonymously } from '$lib/auth';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { theme } from '$lib/stores/theme';
	import logo from '$lib/assets/magellanai_logo.png';

	// Show a message if the user arrives here after a failed OAuth callback.
	let authError = $derived($page.url.searchParams.get('error') === 'auth_callback_failed'
		? 'Sign-in failed. Please try again.'
		: null);

	let googleLoading = $state(false);
	let guestLoading = $state(false);

	let canvas: HTMLCanvasElement;
	let animationId: number;

	async function enterGoogle() {
		googleLoading = true;
		// signInWithGoogle() redirects the browser to Google — no return value needed.
		await signInWithGoogle();
		// If we get here the redirect didn't happen (e.g. popup blocked), reset state.
		googleLoading = false;
	}

	async function enterGuest() {
		guestLoading = true;
		const { error } = (await signInAnonymously()) ?? {};
		if (error) {
			guestLoading = false;
			authError = 'Could not start a guest session. Please try again.';
			return;
		}
		goto('/options');
	}

	// ── Animated star chart ──────────────────────────────────────────────────
	interface Star {
		x: number; y: number;
		r: number;
		vx: number; vy: number;
		opacity: number;
		twinklePhase: number;
		twinkleSpeed: number;
	}

	interface Connection {
		a: number; b: number;
	}

	function initCanvas(isDark: boolean) {
		if (!canvas) return;
		const ctx = canvas.getContext('2d');
		if (!ctx) return;

		let W = canvas.offsetWidth;
		let H = canvas.offsetHeight;
		canvas.width  = W;
		canvas.height = H;

		const NUM_STARS = 140;
		const NUM_CONSTELLATIONS = 10;

		const stars: Star[] = Array.from({ length: NUM_STARS }, () => ({
			x: Math.random() * W,
			y: Math.random() * H,
			r: 0.6 + Math.random() * 2.6,
			vx: (Math.random() - 0.5) * 0.55,
			vy: (Math.random() - 0.5) * 0.40,
			opacity: 0.55 + Math.random() * 0.45,
			twinklePhase: Math.random() * Math.PI * 2,
			twinkleSpeed: 0.032 + Math.random() * 0.055
		}));

		// Build sparse constellation lines between nearby stars
		const connections: Connection[] = [];
		for (let i = 0; i < NUM_CONSTELLATIONS; i++) {
			const start = Math.floor(Math.random() * NUM_STARS);
			let prev = start;
			const lineLen = 2 + Math.floor(Math.random() * 4);
			for (let j = 0; j < lineLen; j++) {
				// Find nearest unused star within 200px
				let best = -1;
				let bestDist = 200;
				for (let k = 0; k < NUM_STARS; k++) {
					if (k === prev) continue;
					const dx = stars[k].x - stars[prev].x;
					const dy = stars[k].y - stars[prev].y;
					const d = Math.sqrt(dx * dx + dy * dy);
					if (d < bestDist) { bestDist = d; best = k; }
				}
				if (best !== -1) {
					connections.push({ a: prev, b: best });
					prev = best;
				}
			}
		}

		let frame = 0;

		function draw() {
			if (!ctx) return;

			// Resize if needed
			if (canvas.offsetWidth !== W || canvas.offsetHeight !== H) {
				W = canvas.width  = canvas.offsetWidth;
				H = canvas.height = canvas.offsetHeight;
				stars.forEach(s => { s.x = Math.random() * W; s.y = Math.random() * H; });
			}

			// Background
			if (isDark) {
				ctx.fillStyle = '#060f1e';
			} else {
				ctx.fillStyle = '#ede8de';
			}
			ctx.fillRect(0, 0, W, H);

			// Subtle radial gradient atmosphere
			const grad = ctx.createRadialGradient(W / 2, H / 2, 0, W / 2, H / 2, Math.max(W, H) * 0.65);
			if (isDark) {
				grad.addColorStop(0, 'rgba(32, 119, 178, 0.07)');
				grad.addColorStop(0.5, 'rgba(201, 168, 76, 0.025)');
				grad.addColorStop(1, 'transparent');
			} else {
				grad.addColorStop(0, 'rgba(26, 92, 138, 0.06)');
				grad.addColorStop(0.5, 'rgba(153, 108, 0, 0.03)');
				grad.addColorStop(1, 'transparent');
			}
			ctx.fillStyle = grad;
			ctx.fillRect(0, 0, W, H);

			frame++;

			// Update star positions (slow drift)
			for (const s of stars) {
				s.x += s.vx;
				s.y += s.vy;
				// Wrap around edges
				if (s.x < -10) s.x = W + 10;
				if (s.x > W + 10) s.x = -10;
				if (s.y < -10) s.y = H + 10;
				if (s.y > H + 10) s.y = -10;
				s.twinklePhase += s.twinkleSpeed;
			}

			// Draw constellation lines
			for (const conn of connections) {
				const a = stars[conn.a];
				const b = stars[conn.b];
				ctx.beginPath();
				ctx.moveTo(a.x, a.y);
				ctx.lineTo(b.x, b.y);
				ctx.strokeStyle = isDark
					? 'rgba(120, 180, 220, 0.14)'
					: 'rgba(26, 39, 68, 0.10)';
				ctx.lineWidth = 0.9;
				ctx.stroke();
			}

			// Draw stars
			for (const s of stars) {
				const twinkle = 0.7 + 0.3 * Math.sin(s.twinklePhase);
				const alpha = s.opacity * twinkle;

				if (s.r > 1.5) {
					// Larger stars get a soft glow
					const glow = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, s.r * 4);
				if (isDark) {
					glow.addColorStop(0, `rgba(0, 212, 240, ${alpha * 0.45})`);
					glow.addColorStop(0.4, `rgba(245, 232, 216, ${alpha * 0.12})`);
					glow.addColorStop(1, 'transparent');
				} else {
					glow.addColorStop(0, `rgba(26, 58, 122, ${alpha * 0.3})`);
					glow.addColorStop(0.4, `rgba(26, 58, 122, ${alpha * 0.08})`);
					glow.addColorStop(1, 'transparent');
				}
					ctx.beginPath();
					ctx.arc(s.x, s.y, s.r * 4, 0, Math.PI * 2);
					ctx.fillStyle = glow;
					ctx.fill();
				}

				// Star core
				ctx.beginPath();
				ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
				ctx.fillStyle = isDark
					? `rgba(245, 232, 216, ${alpha})`
					: `rgba(26, 37, 64, ${alpha * 0.7})`;
				ctx.fill();
			}

			// Subtle coordinate grid overlay
			const gridSpacing = 80;
			const gridAlpha = isDark ? 0.04 : 0.06;
			ctx.strokeStyle = isDark
				? `rgba(30, 51, 82, ${gridAlpha * 10})`
				: `rgba(200, 180, 138, ${gridAlpha * 10})`;
			ctx.lineWidth = 0.5;
			for (let x = 0; x < W; x += gridSpacing) {
				ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
			}
			for (let y = 0; y < H; y += gridSpacing) {
				ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
			}

			animationId = requestAnimationFrame(draw);
		}

		if (animationId) cancelAnimationFrame(animationId);
		draw();
	}

	onMount(() => {
		const isDark = $theme === 'dark';
		initCanvas(isDark);

		// Re-initialize on theme change
		const unsub = theme.subscribe(t => {
			initCanvas(t === 'dark');
		});

		return () => {
			cancelAnimationFrame(animationId);
			unsub();
		};
	});
</script>

<svelte:head>
	<title>MagellanAI — Chart Your Course</title>
</svelte:head>

<div class="scene">
	<!-- Animated star chart background -->
	<canvas bind:this={canvas} class="star-canvas" aria-hidden="true"></canvas>

	<!-- Theme toggle (accessible on sign-in page too) -->
	<button
		type="button"
		class="theme-toggle-corner"
		onclick={() => theme.toggle()}
		aria-label={$theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
	>
		{#if $theme === 'dark'}
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
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
			</svg>
		{/if}
	</button>

	<!-- Hero card -->
	<div class="hero-card">
		<!-- Decorative compass rose corner ornaments -->
		<div class="corner-ornament corner-tl" aria-hidden="true">✦</div>
		<div class="corner-ornament corner-tr" aria-hidden="true">✦</div>
		<div class="corner-ornament corner-bl" aria-hidden="true">✦</div>
		<div class="corner-ornament corner-br" aria-hidden="true">✦</div>

		<!-- Logo -->
		<div class="logo-wrap">
			<img src={logo} alt="MagellanAI — compass rose with circuit patterns" class="hero-logo" />
		</div>

		<!-- Title -->
		<div class="title-wrap">
			<h1 class="brand-title">MagellanAI</h1>
			<div class="title-rule" aria-hidden="true"></div>
			<p class="tagline">Chart Your Academic Voyage</p>
		</div>

		<!-- Description -->
		<p class="description">
			An intelligent course-planning navigator for ECE students at the University of Toronto.
			Describe your interests — we'll plot a complete, constraint-verified semester plan for your
			final two years.
		</p>

		<!-- Divider -->
		<div class="card-divider" aria-hidden="true">
			<span class="divider-symbol">⚓</span>
		</div>

		<!-- Auth error banner -->
		{#if authError}
			<div class="auth-error" role="alert">{authError}</div>
		{/if}

		<!-- Action buttons -->
		<div class="actions">
			<button
				type="button"
				class="btn btn-google"
				onclick={enterGoogle}
				disabled={googleLoading || guestLoading}
			>
				{#if googleLoading}
					<span class="btn-spinner" aria-hidden="true"></span>
					Redirecting…
				{:else}
					<svg class="btn-icon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
						<path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
						<path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
						<path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
						<path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
					</svg>
					Sign in with Google
				{/if}
			</button>
			<button
				type="button"
				class="btn btn-guest"
				onclick={enterGuest}
				disabled={googleLoading || guestLoading}
			>
				{#if guestLoading}
					<span class="btn-spinner btn-spinner-light" aria-hidden="true"></span>
					Starting session…
				{:else}
					<svg class="btn-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
						<path d="M12 2a5 5 0 1 0 0 10A5 5 0 0 0 12 2z"/>
						<path d="M19 21a7 7 0 1 0-14 0"/>
					</svg>
					Continue as Guest
				{/if}
			</button>
		</div>

		<p class="footnote">
			Google sign-in saves your history across sessions. Guest sessions are private to this browser.
		</p>
	</div>

	<!-- Bottom coordinates decoration -->
	<div class="coordinates" aria-hidden="true">
		43°39′N 79°23′W — University of Toronto
	</div>
</div>

<style>
	/* ── Full-screen scene ─────────────────────────────────────────────────── */
	.scene {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		/* Bottom padding clears the fixed coordinate strip */
		padding: 24px 20px 60px;
		position: relative;
		overflow-x: hidden;
		background: var(--bg);
	}

	/* ── Canvas background ─────────────────────────────────────────────────── */
	.star-canvas {
		position: fixed;
		inset: 0;
		width: 100%;
		height: 100%;
		z-index: 0;
		pointer-events: none;
	}

	/* ── Theme toggle corner ───────────────────────────────────────────────── */
	.theme-toggle-corner {
		position: fixed;
		top: 16px;
		right: 16px;
		z-index: 10;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 38px;
		height: 38px;
		border-radius: 50%;
		border: 1px solid var(--border);
		background: var(--surface);
		color: var(--text-muted);
		cursor: pointer;
		transition: all 0.2s ease;
	}
	.theme-toggle-corner:hover {
		border-color: var(--gold-dim);
		color: var(--gold);
		box-shadow: var(--glow-gold);
	}

	/* ── Hero card ─────────────────────────────────────────────────────────── */
	.hero-card {
		position: relative;
		z-index: 5;
		width: min(540px, 100%);
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 20px;
		padding: 32px 36px 28px;
		box-shadow: var(--shadow-lg), var(--glow-ocean);
		text-align: center;
		animation: fade-in 0.7s ease;

		/* Subtle inner glow on card edges */
		outline: 1px solid transparent;
	}

	:global([data-theme='dark']) .hero-card {
		background: linear-gradient(160deg, #111e38 0%, #090f1e 100%);
		box-shadow: var(--shadow-lg), 0 0 60px rgba(0, 212, 240, 0.10), 0 0 40px rgba(218, 165, 32, 0.07);
	}

	/* ── Corner ornaments ──────────────────────────────────────────────────── */
	.corner-ornament {
		position: absolute;
		font-size: 0.7rem;
		color: var(--gold-dim);
		opacity: 0.5;
	}
	.corner-tl { top: 12px; left: 14px; }
	.corner-tr { top: 12px; right: 14px; }
	.corner-bl { bottom: 12px; left: 14px; }
	.corner-br { bottom: 12px; right: 14px; }

	/* ── Logo ──────────────────────────────────────────────────────────────── */
	.logo-wrap {
		display: flex;
		justify-content: center;
		margin-bottom: 16px;
	}

	.hero-logo {
		width: 160px;
		height: 160px;
		object-fit: contain;
		filter: drop-shadow(0 4px 20px rgba(201, 168, 76, 0.35)) drop-shadow(0 0 8px rgba(32, 119, 178, 0.25));
		animation: float 5s ease-in-out infinite;
		transition: filter 0.3s ease;
	}
	.hero-logo:hover {
		filter: drop-shadow(0 4px 28px rgba(201, 168, 76, 0.55)) drop-shadow(0 0 12px rgba(32, 119, 178, 0.4));
	}

	/* ── Title ─────────────────────────────────────────────────────────────── */
	.title-wrap {
		margin-bottom: 18px;
	}

	.brand-title {
		font-family: 'Cinzel', serif;
		font-size: clamp(1.8rem, 5vw, 2.6rem);
		font-weight: 700;
		letter-spacing: 0.1em;
		color: var(--gold);
		text-shadow: 0 0 24px rgba(201, 168, 76, 0.4);
		margin: 0 0 8px;
	}

	.title-rule {
		width: 60px;
		height: 1px;
		background: linear-gradient(90deg, transparent, var(--gold-dim), transparent);
		margin: 0 auto 8px;
	}

	.tagline {
		font-family: 'Cinzel', serif;
		font-size: 0.72rem;
		letter-spacing: 0.25em;
		text-transform: uppercase;
		color: var(--text-muted);
		margin: 0;
	}

	/* ── Description ───────────────────────────────────────────────────────── */
	.description {
		font-size: 0.9rem;
		color: var(--text-muted);
		line-height: 1.65;
		margin: 0 0 22px;
		max-width: 400px;
		margin-left: auto;
		margin-right: auto;
	}

	/* ── Divider ───────────────────────────────────────────────────────────── */
	.card-divider {
		display: flex;
		align-items: center;
		gap: 12px;
		margin: 0 0 22px;
		opacity: 0.35;
	}
	.card-divider::before,
	.card-divider::after {
		content: '';
		flex: 1;
		height: 1px;
		background: var(--gold-dim);
	}
	.divider-symbol {
		font-size: 0.9rem;
		color: var(--gold);
	}

	/* ── Action buttons ────────────────────────────────────────────────────── */
	.actions {
		display: flex;
		flex-direction: column;
		gap: 10px;
		margin-bottom: 18px;
	}

	.btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 10px;
		width: 100%;
		padding: 13px 20px;
		border-radius: 12px;
		font-family: 'Raleway', sans-serif;
		font-size: 0.92rem;
		font-weight: 600;
		letter-spacing: 0.03em;
		border: 1px solid;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.btn-icon {
		flex-shrink: 0;
	}

	.btn-google {
		background: var(--surface-raised);
		color: var(--text);
		border-color: var(--border);
	}
	.btn-google:hover {
		background: var(--surface-hover);
		border-color: var(--ocean-light);
		box-shadow: var(--glow-ocean);
		transform: translateY(-1px);
	}

	.btn-guest {
		background: linear-gradient(135deg, var(--ocean) 0%, var(--ocean-dim) 100%);
		color: #ffffff;
		border-color: var(--ocean-light);
		box-shadow: 0 4px 16px rgba(32, 119, 178, 0.3);
	}
	:global([data-theme='dark']) .btn-guest {
		color: var(--text);
		background: linear-gradient(135deg, rgba(32, 119, 178, 0.25) 0%, rgba(32, 119, 178, 0.1) 100%);
		border-color: var(--ocean);
	}
	.btn-guest:hover {
		transform: translateY(-2px);
		box-shadow: 0 6px 22px rgba(32, 119, 178, 0.45);
		filter: brightness(1.1);
	}

	/* ── Auth error banner ─────────────────────────────────────────────────── */
	.auth-error {
		background: rgba(192, 57, 43, 0.1);
		border: 1px solid rgba(192, 57, 43, 0.35);
		border-radius: 8px;
		padding: 10px 14px;
		font-size: 0.8rem;
		color: var(--compass-red, #c0392b);
		margin-bottom: 4px;
		text-align: center;
	}

	/* ── Button spinner ────────────────────────────────────────────────────── */
	.btn-spinner {
		display: inline-block;
		width: 14px;
		height: 14px;
		border: 2px solid rgba(0, 0, 0, 0.2);
		border-top-color: var(--text);
		border-radius: 50%;
		animation: spin 0.7s linear infinite;
		flex-shrink: 0;
	}
	.btn-spinner-light {
		border-color: rgba(255, 255, 255, 0.3);
		border-top-color: #fff;
	}
	@keyframes spin { to { transform: rotate(360deg); } }

	/* ── Footnote ──────────────────────────────────────────────────────────── */
	.footnote {
		font-size: 0.72rem;
		color: var(--text-faint);
		margin: 0;
		line-height: 1.5;
	}

	/* ── Coordinates strip ─────────────────────────────────────────────────── */
	.coordinates {
		position: fixed;
		bottom: 0;
		left: 0;
		right: 0;
		z-index: 20; /* always above hero-card (z-index: 5) */
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.68rem;
		letter-spacing: 0.12em;
		color: var(--gold);
		opacity: 0.85;
		white-space: nowrap;
		text-align: center;
		padding: 10px 16px 14px;
		/* Gradient backdrop prevents card text bleeding through on short screens */
		background: linear-gradient(to top, var(--bg) 55%, transparent);
		pointer-events: none;
	}

	/* ── Responsive ────────────────────────────────────────────────────────── */
	@media (max-width: 480px) {
		.hero-card {
			padding: 30px 20px 24px;
		}
		.hero-logo {
			width: 80px;
			height: 80px;
		}
	}
</style>

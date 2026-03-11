<script lang="ts">
	import { goto } from '$app/navigation';
	import { signIn } from '$lib/auth';

	function enter(mode: 'guest' | 'google') {
		signIn(mode);
		goto('/options');
	}
</script>

<main class="signin-page">
	<div class="hero-card">
		<h1>MagellanAI</h1>
		<p>
			An intelligent course planning assistant for undergraduate computer and electrical engineering
			students at the University of Toronto
		</p>
		<div class="actions">
			<button type="button" class="primary" on:click={() => enter('google')}>Sign in with Google</button>
			<button type="button" class="secondary" on:click={() => enter('guest')}>Sign in as Guest</button>
		</div>
	</div>
</main>

<style>
	.signin-page {
		min-height: 100vh;
		display: grid;
		place-items: center;
		padding: 20px;
		background:
			radial-gradient(circle at 20% 20%, rgba(59, 130, 246, 0.25), transparent 45%),
			radial-gradient(circle at 80% 80%, rgba(16, 185, 129, 0.2), transparent 45%),
			#f5f8ff;
	}
	.hero-card {
		width: min(760px, 100%);
		text-align: center;
		background: rgba(255, 255, 255, 0.9);
		backdrop-filter: blur(10px);
		border: 1px solid var(--border);
		border-radius: 20px;
		padding: 42px 24px;
		box-shadow: var(--shadow-md);
	}
	h1 {
		margin: 0;
		font-size: clamp(2rem, 5vw, 3rem);
	}
	p {
		margin: 14px auto 24px;
		max-width: 640px;
		color: var(--text-muted);
		line-height: 1.5;
	}
	.actions {
		display: flex;
		justify-content: center;
		gap: 10px;
		flex-wrap: wrap;
	}
	button {
		border: 0;
		border-radius: 12px;
		padding: 12px 18px;
		font-weight: 700;
		cursor: pointer;
	}
	.primary { background: #2563eb; color: white; }
	.secondary { background: #e6ecfa; color: #1e3a8a; }
</style>

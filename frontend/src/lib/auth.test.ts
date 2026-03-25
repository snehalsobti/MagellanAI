/**
 * frontend/src/lib/auth.test.ts
 *
 * Unit tests for auth.ts.
 *
 * auth.ts now wraps Supabase's browser client, so we mock:
 *  - $app/environment  → browser: true
 *  - $env/static/public → Supabase URL / anon key
 *  - @supabase/ssr     → createBrowserClient
 *
 * We verify that the exported functions call the correct Supabase methods
 * with the correct arguments.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ── Mock SvelteKit environment ────────────────────────────────────────────────
vi.mock('$app/environment', () => ({ browser: true }));
vi.mock('$env/static/public', () => ({
	PUBLIC_SUPABASE_URL: 'https://test.supabase.co',
	PUBLIC_SUPABASE_ANON_KEY: 'test-anon-key'
}));

// ── Mock Supabase client ──────────────────────────────────────────────────────
const mockSignInWithOAuth = vi.fn().mockResolvedValue({ data: {}, error: null });
const mockSignInAnonymously = vi.fn().mockResolvedValue({ data: { user: { id: 'anon-id', is_anonymous: true } }, error: null });
const mockSignOut = vi.fn().mockResolvedValue({ error: null });
const mockGetSession = vi.fn().mockResolvedValue({ data: { session: null } });

const mockSupabase = {
	auth: {
		signInWithOAuth: mockSignInWithOAuth,
		signInAnonymously: mockSignInAnonymously,
		signOut: mockSignOut,
		getSession: mockGetSession
	}
};

vi.mock('@supabase/ssr', () => ({
	createBrowserClient: vi.fn(() => mockSupabase)
}));

// ── Tests ─────────────────────────────────────────────────────────────────────
describe('auth module', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.resetModules();
	});

	it('supabase client is created with correct env vars', async () => {
		const { createBrowserClient } = await import('@supabase/ssr');
		// Trigger module load
		await import('./auth');
		expect(createBrowserClient).toHaveBeenCalledWith(
			'https://test.supabase.co',
			'test-anon-key'
		);
	});

	it('signInWithGoogle calls signInWithOAuth with google provider', async () => {
		// Set up window.location.origin
		Object.defineProperty(window, 'location', {
			value: { origin: 'http://localhost:5173' },
			writable: true
		});
		const { signInWithGoogle } = await import('./auth');
		await signInWithGoogle();
		expect(mockSignInWithOAuth).toHaveBeenCalledWith({
			provider: 'google',
			options: { redirectTo: 'http://localhost:5173/auth/callback' }
		});
	});

	it('signInAnonymously calls supabase.auth.signInAnonymously', async () => {
		const { signInAnonymously } = await import('./auth');
		const result = await signInAnonymously();
		expect(mockSignInAnonymously).toHaveBeenCalledOnce();
		expect(result).toMatchObject({ data: { user: { is_anonymous: true } } });
	});

	it('signOut calls supabase.auth.signOut', async () => {
		const { signOut } = await import('./auth');
		await signOut();
		expect(mockSignOut).toHaveBeenCalledOnce();
	});

	it('getSession calls supabase.auth.getSession', async () => {
		const { getSession } = await import('./auth');
		const session = await getSession();
		expect(mockGetSession).toHaveBeenCalledOnce();
		expect(session).toBeNull();
	});

	it('getSession returns session data when one exists', async () => {
		mockGetSession.mockResolvedValueOnce({
			data: { session: { user: { id: 'user-123' }, expires_at: 9999999 } }
		});
		const { getSession } = await import('./auth');
		const session = await getSession();
		expect(session).toMatchObject({ user: { id: 'user-123' } });
	});
});

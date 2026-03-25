import { createBrowserClient } from '@supabase/ssr';
import { browser } from '$app/environment';
import { PUBLIC_SUPABASE_URL, PUBLIC_SUPABASE_ANON_KEY } from '$env/static/public';

/**
 * Singleton browser-side Supabase client.
 * Only instantiated in the browser; null on the server (use event.locals.supabase there).
 */
export const supabase = browser
	? createBrowserClient(PUBLIC_SUPABASE_URL, PUBLIC_SUPABASE_ANON_KEY)
	: null;

/**
 * Initiates Google OAuth 2.0 sign-in.
 * The browser is redirected to Google, then returns to /auth/callback with a code.
 */
export async function signInWithGoogle(): Promise<void> {
	if (!supabase) return;
	const origin = window.location.origin;
	await supabase.auth.signInWithOAuth({
		provider: 'google',
		options: { redirectTo: `${origin}/auth/callback` }
	});
}

/**
 * Signs in as an anonymous guest via Supabase anonymous auth.
 * Creates a real (anonymous) Supabase session stored in cookies, allowing
 * server-side route protection to work. History is persisted in Supabase
 * under the anonymous user_id and cleaned up after 30 days.
 */
export async function signInAnonymously() {
	if (!supabase) return { error: new Error('Not in browser') };
	return supabase.auth.signInAnonymously();
}

/**
 * Signs out the current user (Google or anonymous) and clears the session.
 */
export async function signOut(): Promise<void> {
	if (!supabase) return;
	await supabase.auth.signOut();
}

/**
 * Returns the current session, or null if unauthenticated.
 */
export async function getSession() {
	if (!supabase) return null;
	const { data } = await supabase.auth.getSession();
	return data.session;
}

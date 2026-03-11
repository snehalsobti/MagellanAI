import { browser } from '$app/environment';

const KEY = 'magellan_auth_mode';

export type AuthMode = 'guest' | 'google';

export function signIn(mode: AuthMode) {
	if (!browser) return;
	localStorage.setItem(KEY, mode);
}

export function signOut() {
	if (!browser) return;
	localStorage.removeItem(KEY);
}

export function getAuthMode(): AuthMode | null {
	if (!browser) return null;
	const mode = localStorage.getItem(KEY);
	return mode === 'guest' || mode === 'google' ? mode : null;
}

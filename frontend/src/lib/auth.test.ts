/**
 * frontend/src/lib/auth.test.ts
 *
 * Unit tests for auth.ts:
 * - signIn persists mode to localStorage
 * - signOut removes mode
 * - getAuthMode returns stored mode or null
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

vi.mock('$app/environment', () => ({ browser: true }));

describe('auth utilities', () => {
	beforeEach(() => {
		localStorage.clear();
		vi.resetModules();
	});

	it('signIn stores the auth mode', async () => {
		const { signIn } = await import('./auth');
		signIn('guest');
		expect(localStorage.getItem('magellan_auth_mode')).toBe('guest');
	});

	it('signIn stores google mode', async () => {
		const { signIn } = await import('./auth');
		signIn('google');
		expect(localStorage.getItem('magellan_auth_mode')).toBe('google');
	});

	it('signOut removes the key', async () => {
		const { signIn, signOut } = await import('./auth');
		signIn('guest');
		signOut();
		expect(localStorage.getItem('magellan_auth_mode')).toBeNull();
	});

	it('getAuthMode returns null when not signed in', async () => {
		const { getAuthMode } = await import('./auth');
		expect(getAuthMode()).toBeNull();
	});

	it('getAuthMode returns guest after signIn', async () => {
		const { signIn, getAuthMode } = await import('./auth');
		signIn('guest');
		expect(getAuthMode()).toBe('guest');
	});

	it('getAuthMode returns google after signIn', async () => {
		const { signIn, getAuthMode } = await import('./auth');
		signIn('google');
		expect(getAuthMode()).toBe('google');
	});

	it('getAuthMode returns null after signOut', async () => {
		const { signIn, signOut, getAuthMode } = await import('./auth');
		signIn('guest');
		signOut();
		expect(getAuthMode()).toBeNull();
	});

	it('getAuthMode rejects invalid stored values', async () => {
		localStorage.setItem('magellan_auth_mode', 'admin'); // invalid
		const { getAuthMode } = await import('./auth');
		expect(getAuthMode()).toBeNull();
	});
});

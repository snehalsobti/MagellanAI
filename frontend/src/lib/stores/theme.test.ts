/**
 * frontend/src/lib/stores/theme.test.ts
 *
 * Unit tests for the theme store.
 * Tests the dark/light mode toggle logic and localStorage persistence
 * without involving browser-specific APIs (jsdom provides them).
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

// ── Mocks ──────────────────────────────────────────────────────────────────
// Mock $app/environment so 'browser' resolves to true in tests
vi.mock('$app/environment', () => ({ browser: true }));

// ── Helpers ────────────────────────────────────────────────────────────────

function freshStore() {
	// Reset module registry so each test gets a pristine store instance
	vi.resetModules();
	return import('./theme');
}

describe('theme store', () => {
	beforeEach(() => {
		localStorage.clear();
		// Reset data-theme attribute
		document.documentElement.removeAttribute('data-theme');
	});

	it('defaults to dark mode when localStorage is empty', async () => {
		const { theme } = await freshStore();
		let value: string | undefined;
		const unsub = theme.subscribe((v) => (value = v));
		expect(value).toBe('dark');
		unsub();
	});

	it('restores saved theme from localStorage', async () => {
		localStorage.setItem('magellan_theme', 'light');
		const { theme } = await freshStore();
		let value: string | undefined;
		const unsub = theme.subscribe((v) => (value = v));
		expect(value).toBe('light');
		unsub();
	});

	it('toggle switches dark → light', async () => {
		const { theme } = await freshStore();
		const values: string[] = [];
		const unsub = theme.subscribe((v) => values.push(v));
		theme.toggle();
		expect(values).toEqual(['dark', 'light']);
		unsub();
	});

	it('toggle switches light → dark', async () => {
		localStorage.setItem('magellan_theme', 'light');
		const { theme } = await freshStore();
		const values: string[] = [];
		const unsub = theme.subscribe((v) => values.push(v));
		theme.toggle();
		expect(values).toEqual(['light', 'dark']);
		unsub();
	});

	it('set() persists to localStorage', async () => {
		const { theme } = await freshStore();
		theme.set('light');
		expect(localStorage.getItem('magellan_theme')).toBe('light');
	});

	it('set() applies data-theme attribute to documentElement', async () => {
		const { theme } = await freshStore();
		theme.set('light');
		expect(document.documentElement.getAttribute('data-theme')).toBe('light');
		theme.set('dark');
		expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
	});

	it('toggle persists new value to localStorage', async () => {
		const { theme } = await freshStore();
		theme.toggle(); // dark → light
		expect(localStorage.getItem('magellan_theme')).toBe('light');
		theme.toggle(); // light → dark
		expect(localStorage.getItem('magellan_theme')).toBe('dark');
	});
});

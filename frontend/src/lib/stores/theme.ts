import { browser } from '$app/environment';
import { writable } from 'svelte/store';

export type ThemeMode = 'dark' | 'light';

const STORAGE_KEY = 'magellan_theme';
const DEFAULT: ThemeMode = 'dark';

function createThemeStore() {
	const initial: ThemeMode =
		browser
			? ((localStorage.getItem(STORAGE_KEY) as ThemeMode | null) ?? DEFAULT)
			: DEFAULT;

	const { subscribe, set } = writable<ThemeMode>(initial);

	function apply(mode: ThemeMode) {
		if (browser) {
			document.documentElement.setAttribute('data-theme', mode);
			localStorage.setItem(STORAGE_KEY, mode);
		}
		set(mode);
	}

	// Apply immediately on load
	if (browser) {
		document.documentElement.setAttribute('data-theme', initial);
	}

	return {
		subscribe,
		toggle() {
			const current = browser
				? ((localStorage.getItem(STORAGE_KEY) as ThemeMode | null) ?? DEFAULT)
				: DEFAULT;
			apply(current === 'dark' ? 'light' : 'dark');
		},
		set: apply
	};
}

export const theme = createThemeStore();

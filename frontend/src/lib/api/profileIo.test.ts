/**
 * Unit tests for profile export / import (Feature 7).
 *
 * Covers:
 *  - importProfile: valid export round-trips
 *  - importProfile: rejects wrong version
 *  - importProfile: rejects missing profile field
 *  - importProfile: rejects invalid JSON
 *  - importProfile: rejects missing courses array
 *  - exportProfile: creates a downloadable blob (DOM environment)
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { importProfile, exportProfile } from './profileIo';
import type { ProfileExport } from './profileIo';
import type { ProfileResponse } from '$lib/types/profile';

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeValidExport(overrides: Partial<ProfileExport> = {}): ProfileExport {
	return {
		version: 1,
		exported_at: '2026-03-26T00:00:00.000Z',
		interests: 'machine learning',
		year12_choice: 'ECE297H1',
		profile: {
			success: true,
			courses: [{ course_code: 'ECE421H1', course_name: 'ML', area: 5, num_credits: 0.5, kernel_course: false, technical_elective: true }],
			semester_plan: [],
			total_credits: 0.5,
			kernel_areas_selected: [5],
			depth_areas_selected: [5],
			preferences_used: [],
			preferences_skipped: [],
			constraints_satisfied: true
		} as ProfileResponse,
		feedback: { ECE421H1: 'LIKE' },
		original_preferences: ['ECE421H1'],
		...overrides
	};
}

/**
 * Creates a File from a string, simulating a user-selected file in the browser.
 */
function makeFile(content: string, name = 'profile.json'): File {
	const blob = new Blob([content], { type: 'application/json' });
	return new File([blob], name, { type: 'application/json' });
}

// ── importProfile tests ──────────────────────────────────────────────────────

describe('importProfile', () => {
	it('resolves with valid v1 export data', async () => {
		const data = makeValidExport();
		const file = makeFile(JSON.stringify(data));
		const result = await importProfile(file);

		expect(result.version).toBe(1);
		expect(result.interests).toBe('machine learning');
		expect(result.year12_choice).toBe('ECE297H1');
		expect(result.profile.courses).toHaveLength(1);
		expect(result.feedback).toEqual({ ECE421H1: 'LIKE' });
		expect(result.original_preferences).toEqual(['ECE421H1']);
	});

	it('resolves even when feedback and preferences are empty', async () => {
		const data = makeValidExport({ feedback: {}, original_preferences: [] });
		const file = makeFile(JSON.stringify(data));
		const result = await importProfile(file);
		expect(result.feedback).toEqual({});
		expect(result.original_preferences).toEqual([]);
	});

	it('rejects when version is not 1', async () => {
		const bad = { ...makeValidExport(), version: 2 };
		const file = makeFile(JSON.stringify(bad));
		await expect(importProfile(file)).rejects.toThrow(/unrecognised file format/i);
	});

	it('rejects when version field is missing', async () => {
		const { version: _, ...bad } = makeValidExport() as any;
		const file = makeFile(JSON.stringify(bad));
		await expect(importProfile(file)).rejects.toThrow(/unrecognised file format/i);
	});

	it('rejects when profile field is missing', async () => {
		const { profile: _, ...bad } = makeValidExport() as any;
		const file = makeFile(JSON.stringify(bad));
		await expect(importProfile(file)).rejects.toThrow(/invalid profile file/i);
	});

	it('rejects when profile.courses is not an array', async () => {
		const bad = makeValidExport();
		(bad.profile as any).courses = null;
		const file = makeFile(JSON.stringify(bad));
		await expect(importProfile(file)).rejects.toThrow(/invalid profile file/i);
	});

	it('rejects on completely invalid JSON', async () => {
		const file = makeFile('{ this is not json }');
		await expect(importProfile(file)).rejects.toThrow(/failed to parse/i);
	});

	it('rejects on empty file content', async () => {
		const file = makeFile('');
		await expect(importProfile(file)).rejects.toThrow();
	});

	it('rejects when root is null', async () => {
		const file = makeFile('null');
		await expect(importProfile(file)).rejects.toThrow(/unrecognised file format/i);
	});
});

// ── exportProfile tests ──────────────────────────────────────────────────────

describe('exportProfile', () => {
	afterEach(() => {
		vi.restoreAllMocks();
	});

	it('creates a blob URL and triggers a download', () => {
		const mockRevoke = vi.fn();
		const mockCreateObjectURL = vi.fn(() => 'blob:mock-url');
		vi.stubGlobal('URL', { createObjectURL: mockCreateObjectURL, revokeObjectURL: mockRevoke });

		const clickSpy = vi.fn();
		vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
			if (tag === 'a') {
				const a = { href: '', download: '', click: clickSpy } as any;
				return a;
			}
			return document.createElement(tag);
		});

		const data = makeValidExport();
		exportProfile(
			data.profile,
			data.feedback,
			data.original_preferences,
			data.interests,
			data.year12_choice
		);

		expect(mockCreateObjectURL).toHaveBeenCalledOnce();
		expect(clickSpy).toHaveBeenCalledOnce();
		expect(mockRevoke).toHaveBeenCalledWith('blob:mock-url');
	});

	it('sets a filename with the current date', () => {
		const mockRevoke = vi.fn();
		vi.stubGlobal('URL', {
			createObjectURL: vi.fn(() => 'blob:mock-url'),
			revokeObjectURL: mockRevoke
		});

		let capturedDownload = '';
		vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
			if (tag === 'a') {
				const a = {
					href: '',
					set download(v: string) { capturedDownload = v; },
					click: vi.fn()
				} as any;
				return a;
			}
			return document.createElement(tag);
		});

		const data = makeValidExport();
		exportProfile(data.profile, data.feedback, data.original_preferences, data.interests, data.year12_choice);

		expect(capturedDownload).toMatch(/^magellan-profile-\d{4}-\d{2}-\d{2}\.json$/);
	});
});

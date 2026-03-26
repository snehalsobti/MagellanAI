/**
 * Local file-based profile export and import (Feature 7).
 *
 * Export writes a JSON snapshot to the user's device.
 * Import reads and validates a previously exported snapshot.
 * Both work for guest (anonymous) and Google-authenticated users.
 */

import type { ProfileResponse } from '$lib/types/profile';
import type { FeedbackRecord } from '$lib/types/feedback';

export interface ProfileExport {
	version: 1;
	exported_at: string;
	interests: string;
	year12_choice: string;
	profile: ProfileResponse;
	feedback: FeedbackRecord;
	original_preferences: string[];
}

/**
 * Serialises the current profile state to a JSON file and triggers a browser download.
 */
export function exportProfile(
	profile: ProfileResponse,
	feedback: FeedbackRecord,
	originalPreferences: string[],
	interests: string,
	year12Choice: string
): void {
	const payload: ProfileExport = {
		version: 1,
		exported_at: new Date().toISOString(),
		interests,
		year12_choice: year12Choice,
		profile,
		feedback,
		original_preferences: originalPreferences
	};
	const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
	const url = URL.createObjectURL(blob);
	const anchor = document.createElement('a');
	anchor.href = url;
	anchor.download = `magellan-profile-${new Date().toISOString().slice(0, 10)}.json`;
	anchor.click();
	URL.revokeObjectURL(url);
}

/**
 * Reads a File object, parses and validates it as a MagellanAI profile export.
 * Rejects with a user-friendly error message on failure.
 */
export function importProfile(file: File): Promise<ProfileExport> {
	return new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = (e) => {
			try {
				const raw = JSON.parse(e.target?.result as string);
				if (!raw || raw.version !== 1) {
					reject(new Error('Unrecognised file format — expected a MagellanAI v1 export.'));
					return;
				}
				if (!raw.profile?.courses || !Array.isArray(raw.profile.courses)) {
					reject(new Error('Invalid profile file — missing course data.'));
					return;
				}
				resolve(raw as ProfileExport);
			} catch {
				reject(new Error('Failed to parse file. Make sure it is a valid MagellanAI JSON export.'));
			}
		};
		reader.onerror = () => reject(new Error('Failed to read the selected file.'));
		reader.readAsText(file);
	});
}

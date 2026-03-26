/**
 * Supabase-backed saved profiles for Google-authenticated users (Feature 4).
 *
 * Manual setup — run once in the Supabase SQL editor:
 *
 *   CREATE TABLE IF NOT EXISTS saved_profiles (
 *     id                   UUID         DEFAULT gen_random_uuid() PRIMARY KEY,
 *     user_id              UUID         REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
 *     name                 TEXT         NOT NULL DEFAULT 'Untitled Profile',
 *     year12_choice        TEXT,
 *     interests            TEXT,
 *     profile              JSONB        NOT NULL,
 *     original_preferences JSONB        NOT NULL DEFAULT '[]',
 *     feedback             JSONB        NOT NULL DEFAULT '{}',
 *     saved_at             TIMESTAMPTZ  DEFAULT NOW()
 *   );
 *
 *   CREATE INDEX IF NOT EXISTS idx_saved_profiles_user
 *     ON saved_profiles(user_id, saved_at DESC);
 *
 *   ALTER TABLE saved_profiles ENABLE ROW LEVEL SECURITY;
 *   CREATE POLICY "saved_select_own" ON saved_profiles
 *     FOR SELECT USING (auth.uid() = user_id);
 *   CREATE POLICY "saved_insert_own" ON saved_profiles
 *     FOR INSERT WITH CHECK (auth.uid() = user_id);
 *   CREATE POLICY "saved_delete_own" ON saved_profiles
 *     FOR DELETE USING (auth.uid() = user_id);
 */

import type { SupabaseClient } from '@supabase/supabase-js';
import type { ProfileResponse } from '$lib/types/profile';
import type { FeedbackRecord } from '$lib/types/feedback';

const TABLE = 'saved_profiles';
export const SAVE_LIMIT = 10;

export interface SavedProfile {
	id: string;
	name: string;
	year12_choice: string | null;
	interests: string | null;
	profile: ProfileResponse;
	original_preferences: string[];
	feedback: FeedbackRecord;
	saved_at: string;
}

/** Lists all saved profiles for the current user, newest first. */
export async function listSavedProfiles(supabase: SupabaseClient): Promise<SavedProfile[]> {
	const { data, error } = await supabase
		.from(TABLE)
		.select('id, name, year12_choice, interests, profile, original_preferences, feedback, saved_at')
		.order('saved_at', { ascending: false });

	if (error) {
		console.error('[savedProfiles] listSavedProfiles failed:', error.message);
		return [];
	}
	return (data ?? []) as SavedProfile[];
}

/**
 * Saves the current profile under a user-supplied name.
 * Returns an error string if the save limit is reached or the insert fails.
 */
export async function saveProfile(
	supabase: SupabaseClient,
	name: string,
	profile: ProfileResponse,
	originalPreferences: string[],
	feedback: FeedbackRecord,
	year12Choice: string,
	interests: string
): Promise<{ error: string | null }> {
	const {
		data: { user }
	} = await supabase.auth.getUser();
	if (!user) return { error: 'Not authenticated.' };

	// Enforce per-user save cap.
	const { data: existing } = await supabase.from(TABLE).select('id');
	if (existing && existing.length >= SAVE_LIMIT) {
		return {
			error: `Save limit reached (${SAVE_LIMIT} profiles). Delete a profile to free up space.`
		};
	}

	const { error } = await supabase.from(TABLE).insert({
		user_id: user.id,
		name,
		profile,
		original_preferences: originalPreferences,
		feedback,
		year12_choice: year12Choice,
		interests
	});

	if (error) {
		console.error('[savedProfiles] saveProfile failed:', error.message);
		return { error: error.message };
	}
	return { error: null };
}

/** Permanently deletes a saved profile by its UUID. */
export async function deleteSavedProfile(
	supabase: SupabaseClient,
	id: string
): Promise<{ error: string | null }> {
	const { error } = await supabase.from(TABLE).delete().eq('id', id);
	if (error) {
		console.error('[savedProfiles] deleteSavedProfile failed:', error.message);
		return { error: error.message };
	}
	return { error: null };
}

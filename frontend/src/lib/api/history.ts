/**
 * Supabase-backed persistence for generation history.
 *
 * Schema (run once in the Supabase SQL editor — see manual setup steps):
 *
 *   CREATE TABLE generation_history (
 *     id                   UUID         DEFAULT gen_random_uuid() PRIMARY KEY,
 *     user_id              UUID         REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
 *     iteration            INTEGER      NOT NULL,
 *     profile              JSONB        NOT NULL,
 *     feedback             JSONB        NOT NULL DEFAULT '{}',
 *     original_preferences JSONB        NOT NULL DEFAULT '[]',
 *     year12_choice        TEXT,
 *     created_at           TIMESTAMPTZ  DEFAULT NOW()
 *   );
 *
 *   CREATE INDEX ON generation_history(user_id, created_at DESC);
 *
 *   ALTER TABLE generation_history ENABLE ROW LEVEL SECURITY;
 *   CREATE POLICY "users_select_own" ON generation_history FOR SELECT USING (auth.uid() = user_id);
 *   CREATE POLICY "users_insert_own" ON generation_history FOR INSERT WITH CHECK (auth.uid() = user_id);
 *   CREATE POLICY "users_delete_own" ON generation_history FOR DELETE USING (auth.uid() = user_id);
 */

import type { SupabaseClient } from '@supabase/supabase-js';
import type { HistoryEntry } from '$lib/types/feedback';
import { HISTORY_LIMIT } from '$lib/types/feedback';

const TABLE = 'generation_history';

export interface PersistedSession {
	entries: HistoryEntry[];
	originalPreferences: string[];
	year12Choice: string | null;
}

/**
 * Loads the most recent generation session for the authenticated user.
 * Returns entries sorted oldest-first (iteration ascending).
 */
export async function loadSession(supabase: SupabaseClient): Promise<PersistedSession> {
	const { data, error } = await supabase
		.from(TABLE)
		.select('iteration, profile, feedback, original_preferences, year12_choice, created_at')
		.order('created_at', { ascending: true })
		.limit(HISTORY_LIMIT);

	if (error || !data || data.length === 0) {
		return { entries: [], originalPreferences: [], year12Choice: null };
	}

	const entries: HistoryEntry[] = data.map((row) => ({
		iteration: row.iteration,
		profile: row.profile,
		feedback: row.feedback,
		timestamp: new Date(row.created_at).getTime()
	}));

	const latest = data[data.length - 1];
	return {
		entries,
		originalPreferences: latest.original_preferences ?? [],
		year12Choice: latest.year12_choice ?? null
	};
}

/**
 * Appends a single history entry. Prunes entries beyond HISTORY_LIMIT by
 * deleting the oldest ones first (cheapest strategy at this scale).
 */
export async function appendEntry(
	supabase: SupabaseClient,
	entry: HistoryEntry,
	originalPreferences: string[],
	year12Choice: string | null
): Promise<void> {
	const {
		data: { user }
	} = await supabase.auth.getUser();
	if (!user) return;

	const { error } = await supabase.from(TABLE).insert({
		user_id: user.id,
		iteration: entry.iteration,
		profile: entry.profile,
		feedback: entry.feedback,
		original_preferences: originalPreferences,
		year12_choice: year12Choice
	});
	if (error) console.error('[history] appendEntry failed:', error.message);

	// Prune: keep only the most recent HISTORY_LIMIT rows for this user.
	// Always filter by user_id explicitly rather than relying solely on RLS,
	// so this is safe even if RLS is ever relaxed or bypassed.
	const { data: rows } = await supabase
		.from(TABLE)
		.select('id, created_at')
		.eq('user_id', user.id)
		.order('created_at', { ascending: false });

	if (rows && rows.length > HISTORY_LIMIT) {
		const toDelete = rows.slice(HISTORY_LIMIT).map((r: { id: string }) => r.id);
		await supabase.from(TABLE).delete().in('id', toDelete);
	}
}

/**
 * Clears all history for the current user.
 * Called when the user starts a fresh generation ("Generate Fresh" button).
 */
export async function clearSession(supabase: SupabaseClient): Promise<void> {
	const {
		data: { user }
	} = await supabase.auth.getUser();
	if (!user) return;
	const { error } = await supabase.from(TABLE).delete().eq('user_id', user.id);
	if (error) console.error('[history] clearSession failed:', error.message);
}

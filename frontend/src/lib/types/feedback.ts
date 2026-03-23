import type { ProfileResponse } from './profile';

/** The four mutually-exclusive feedback states a course slot can hold. */
export type FeedbackState = 'LOCK' | 'EXCLUDE' | 'LIKE' | 'DISLIKE';

/**
 * Maps course_code → feedback state for the current (editable) iteration.
 * Keyed by course code so capstone double-slots (same code, two grid cells)
 * are automatically synchronised without any extra logic.
 */
export type FeedbackRecord = Record<string, FeedbackState>;

/**
 * Report returned by the backend about which LIKE/DISLIKE courses were honoured.
 * LIKE:    honored = placed in profile;   skipped = not placed (constraint conflict).
 * DISLIKE: honored = not placed (penalty worked); forced = still placed (constraints required it).
 */
export interface FeedbackHonorReport {
	liked_honored: string[];
	liked_skipped: string[];
	disliked_honored: string[];
	disliked_forced: string[];
}

/**
 * A single entry in the iteration history.
 * ``feedback`` captures what was submitted to produce the NEXT iteration
 * (i.e. the feedback that was active when "Regenerate" was clicked).
 * Past entries are immutable and displayed read-only.
 */
export interface HistoryEntry {
	iteration: number;
	profile: ProfileResponse;
	/** Feedback that was applied to produce the next iteration. */
	feedback: FeedbackRecord;
	timestamp: number;
}

/** Maximum number of past iterations kept in the session-only history. */
export const HISTORY_LIMIT = 10;

/** Capstone course codes (mirrors the SSOT list). */
export const CAPSTONE_CODES: ReadonlySet<string> = new Set([
	'ECE496Y1',
	'APS490Y1',
	'BME498Y1'
]);

/** Returns true if the given course code is a capstone. */
export function isCapstoneCode(code: string): boolean {
	return CAPSTONE_CODES.has(code);
}

/** Human-readable label + emoji for each feedback state. */
export const FEEDBACK_LABELS: Record<FeedbackState, string> = {
	LOCK: '🔒 Lock',
	EXCLUDE: '❌ Exclude',
	LIKE: '👍 Like',
	DISLIKE: '👎 Dislike'
};

/** CSS class suffix used for colour-coding grid cells and memory panel entries. */
export const FEEDBACK_CSS_CLASS: Record<FeedbackState, string> = {
	LOCK: 'fb-lock',
	EXCLUDE: 'fb-exclude',
	LIKE: 'fb-like',
	DISLIKE: 'fb-dislike'
};

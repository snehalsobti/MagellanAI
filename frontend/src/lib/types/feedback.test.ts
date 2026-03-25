/**
 * frontend/src/lib/types/feedback.test.ts
 *
 * Unit tests for feedback type utilities:
 * - isCapstoneCode
 * - FEEDBACK_LABELS
 * - FEEDBACK_CSS_CLASS
 * - HISTORY_LIMIT constant
 * - CAPSTONE_CODES set membership
 */
import { describe, it, expect } from 'vitest';
import {
	isCapstoneCode,
	FEEDBACK_LABELS,
	FEEDBACK_CSS_CLASS,
	CAPSTONE_CODES,
	HISTORY_LIMIT
} from './feedback';

describe('isCapstoneCode', () => {
	it('returns true for ECE496Y1', () => {
		expect(isCapstoneCode('ECE496Y1')).toBe(true);
	});

	it('returns true for APS490Y1', () => {
		expect(isCapstoneCode('APS490Y1')).toBe(true);
	});

	it('returns true for BME498Y1', () => {
		expect(isCapstoneCode('BME498Y1')).toBe(true);
	});

	it('returns false for a regular course', () => {
		expect(isCapstoneCode('ECE421H1')).toBe(false);
	});

	it('returns false for ECE472H1 (required, not capstone)', () => {
		expect(isCapstoneCode('ECE472H1')).toBe(false);
	});

	it('is case-sensitive (lowercase does not match)', () => {
		expect(isCapstoneCode('ece496y1')).toBe(false);
	});
});

describe('CAPSTONE_CODES set', () => {
	it('contains exactly the three canonical capstone codes', () => {
		expect(CAPSTONE_CODES.size).toBe(3);
		expect(CAPSTONE_CODES.has('ECE496Y1')).toBe(true);
		expect(CAPSTONE_CODES.has('APS490Y1')).toBe(true);
		expect(CAPSTONE_CODES.has('BME498Y1')).toBe(true);
	});
});

describe('FEEDBACK_LABELS', () => {
	it('has labels for all four states', () => {
		expect(FEEDBACK_LABELS.LOCK).toContain('Lock');
		expect(FEEDBACK_LABELS.EXCLUDE).toContain('Exclude');
		expect(FEEDBACK_LABELS.LIKE).toContain('Like');
		expect(FEEDBACK_LABELS.DISLIKE).toContain('Dislike');
	});
});

describe('FEEDBACK_CSS_CLASS', () => {
	it('maps each state to the correct CSS class', () => {
		expect(FEEDBACK_CSS_CLASS.LOCK).toBe('fb-lock');
		expect(FEEDBACK_CSS_CLASS.EXCLUDE).toBe('fb-exclude');
		expect(FEEDBACK_CSS_CLASS.LIKE).toBe('fb-like');
		expect(FEEDBACK_CSS_CLASS.DISLIKE).toBe('fb-dislike');
	});
});

describe('HISTORY_LIMIT', () => {
	it('is exactly 10', () => {
		expect(HISTORY_LIMIT).toBe(10);
	});
});

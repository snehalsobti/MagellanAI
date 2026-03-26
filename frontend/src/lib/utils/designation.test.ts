/**
 * Unit tests for CE / EE designation logic (Feature 8).
 *
 * Covers:
 *  - EE designation: ≥ 5 breadth+depth courses from Areas 1–4
 *  - CE designation: ≥ 4 breadth+depth courses from Areas 5–6
 *  - Dual CE / EE (edge case, mathematically possible only with mixed depth)
 *  - Null return when neither threshold is met
 *  - Fallback path (no constraint_diagnostics buckets present)
 *  - Profiles with all-computer and all-electrical areas
 */

import { describe, it, expect } from 'vitest';
import { computeDesignation } from './designation';
import type { ProfileResponse } from '$lib/types/profile';

// Minimal ProfileResponse factory — only fills fields needed by computeDesignation.
function makeProfile(overrides: Partial<ProfileResponse> = {}): ProfileResponse {
	return {
		success: true,
		courses: [],
		semester_plan: [],
		total_credits: 10,
		kernel_areas_selected: [],
		depth_areas_selected: [],
		preferences_used: [],
		preferences_skipped: [],
		constraints_satisfied: true,
		...overrides
	};
}

// Helper: build a kernel_depth_by_area bucket entry.
function bucket(area: number, numCourses: number) {
	return { area, course_codes: Array.from({ length: numCourses }, (_, i) => `ECE${area}0${i}H1`) };
}

describe('computeDesignation — via constraint_diagnostics buckets', () => {
	it('returns EE when all 8 courses are from Areas 1–4', () => {
		// Standard EE profile: 2 depth areas in {1,2} (3 courses each) + 2 breadth-only in {3,4}
		const p = makeProfile({
			constraint_diagnostics: {
				ok: true,
				failed_checks: [],
				ceab_failures: [],
				requirement_buckets: {
					kernel_depth_by_area: [
						bucket(1, 3), // depth area → 1 kernel + 2 extras
						bucket(2, 3), // depth area
						bucket(3, 1), // breadth-only
						bucket(4, 1)  // breadth-only
					],
					engineering_economics: [],
					capstone: [],
					science_math: [],
					technical_electives: [],
					hss_cs: [],
					free_elective: []
				}
			}
		});
		const result = computeDesignation(p);
		expect(result).not.toBeNull();
		expect(result!.ee).toBe(true);
		expect(result!.ce).toBe(false);
		expect(result!.label).toBe('EE');
	});

	it('returns CE when ≥ 4 courses are from Areas 5–6', () => {
		// CE profile: both depth areas in {5,6}, 2 breadth-only from {1,2}
		const p = makeProfile({
			constraint_diagnostics: {
				ok: true,
				failed_checks: [],
				ceab_failures: [],
				requirement_buckets: {
					kernel_depth_by_area: [
						bucket(1, 1),
						bucket(2, 1),
						bucket(5, 3), // depth → 3 courses from area 5
						bucket(6, 3)  // depth → 3 courses from area 6
					],
					engineering_economics: [],
					capstone: [],
					science_math: [],
					technical_electives: [],
					hss_cs: [],
					free_elective: []
				}
			}
		});
		const result = computeDesignation(p);
		expect(result).not.toBeNull();
		expect(result!.ce).toBe(true);
		expect(result!.ee).toBe(false);
		expect(result!.label).toBe('CE');
	});

	it('returns CE when exactly 4 courses are from Areas 5–6', () => {
		// 1 depth in area 5 (3), 1 breadth-only in area 6 (1), rest electrical
		const p = makeProfile({
			constraint_diagnostics: {
				ok: true,
				failed_checks: [],
				ceab_failures: [],
				requirement_buckets: {
					kernel_depth_by_area: [
						bucket(1, 3), // depth
						bucket(2, 1),
						bucket(5, 3), // depth
						bucket(6, 1)  // breadth-only in area 6 → total computer = 4
					],
					engineering_economics: [],
					capstone: [],
					science_math: [],
					technical_electives: [],
					hss_cs: [],
					free_elective: []
				}
			}
		});
		const result = computeDesignation(p);
		expect(result).not.toBeNull();
		expect(result!.ce).toBe(true);
		expect(result!.label).toBe('CE');
	});

	it('returns EE when exactly 5 courses are from Areas 1–4', () => {
		// 1 depth area 1 (3), 2 breadth-only in areas 2,3 (2), 1 depth area 5 (3) — total ee=5
		const p = makeProfile({
			constraint_diagnostics: {
				ok: true,
				failed_checks: [],
				ceab_failures: [],
				requirement_buckets: {
					kernel_depth_by_area: [
						bucket(1, 3),
						bucket(2, 1),
						bucket(3, 1),
						bucket(5, 3)
					],
					engineering_economics: [],
					capstone: [],
					science_math: [],
					technical_electives: [],
					hss_cs: [],
					free_elective: []
				}
			}
		});
		const result = computeDesignation(p);
		expect(result).not.toBeNull();
		expect(result!.ee).toBe(true);
		expect(result!.label).toBe('EE');
	});

	it('returns null when neither threshold is met', () => {
		// comp=3 (area 5 depth, 3 courses) < 4; elec=1+1+1=3 < 5 → neither threshold
		const p = makeProfile({
			constraint_diagnostics: {
				ok: true,
				failed_checks: [],
				ceab_failures: [],
				requirement_buckets: {
					kernel_depth_by_area: [
						bucket(5, 3),  // 3 computer courses — just below CE threshold of 4
						bucket(1, 1),
						bucket(2, 1),
						bucket(3, 1)
					],
					engineering_economics: [],
					capstone: [],
					science_math: [],
					technical_electives: [],
					hss_cs: [],
					free_elective: []
				}
			}
		});
		const result = computeDesignation(p);
		expect(result).toBeNull();
	});

	it('returns CE / EE when both thresholds are met', () => {
		// Synthetic: 4 from {5,6} and 5 from {1-4} — impossible with 8 total but test the logic
		const p = makeProfile({
			constraint_diagnostics: {
				ok: true,
				failed_checks: [],
				ceab_failures: [],
				requirement_buckets: {
					kernel_depth_by_area: [
						bucket(1, 3),
						bucket(2, 3),
						bucket(5, 2),
						bucket(6, 2)
					],
					engineering_economics: [],
					capstone: [],
					science_math: [],
					technical_electives: [],
					hss_cs: [],
					free_elective: []
				}
			}
		});
		// electrical=6, computer=4 → both
		const result = computeDesignation(p);
		expect(result).not.toBeNull();
		expect(result!.ce).toBe(true);
		expect(result!.ee).toBe(true);
		expect(result!.label).toBe('CE / EE');
	});

	it('returns null for empty buckets', () => {
		const p = makeProfile({
			constraint_diagnostics: {
				ok: true,
				failed_checks: [],
				ceab_failures: [],
				requirement_buckets: {
					kernel_depth_by_area: [],
					engineering_economics: [],
					capstone: [],
					science_math: [],
					technical_electives: [],
					hss_cs: [],
					free_elective: []
				}
			}
		});
		// Falls to fallback path with empty kernel_areas_selected → null
		expect(computeDesignation(p)).toBeNull();
	});
});

describe('computeDesignation — fallback path (no constraint_diagnostics)', () => {
	it('returns EE via fallback when depth areas are 1 and 2', () => {
		// kernel areas [1,2,3,4], depth [1,2] → 3+3+1+1=8, electrical=8 ≥5 → EE
		const p = makeProfile({
			kernel_areas_selected: [1, 2, 3, 4],
			depth_areas_selected: [1, 2]
		});
		const result = computeDesignation(p);
		expect(result).not.toBeNull();
		expect(result!.ee).toBe(true);
		expect(result!.ce).toBe(false);
		expect(result!.label).toBe('EE');
	});

	it('returns CE via fallback when depth areas are 5 and 6', () => {
		// kernel [1,2,5,6], depth [5,6] → elec=1+1=2, comp=3+3=6 ≥4 → CE
		const p = makeProfile({
			kernel_areas_selected: [1, 2, 5, 6],
			depth_areas_selected: [5, 6]
		});
		const result = computeDesignation(p);
		expect(result).not.toBeNull();
		expect(result!.ce).toBe(true);
		expect(result!.ee).toBe(false);
		expect(result!.label).toBe('CE');
	});

	it('returns null via fallback when no areas selected', () => {
		const p = makeProfile({
			kernel_areas_selected: [],
			depth_areas_selected: []
		});
		expect(computeDesignation(p)).toBeNull();
	});
});

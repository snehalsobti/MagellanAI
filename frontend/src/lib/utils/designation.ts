/**
 * CE / EE degree designation logic (Feature 8).
 *
 * Rules (University of Toronto ECE):
 *  CE: ≥ 4 of the 8 breadth+depth courses are from Areas 5–6 (Computer Engineering)
 *  EE: ≥ 5 of the 8 breadth+depth courses are from Areas 1–4 (Electrical Engineering)
 *
 * The 8 courses are: one kernel from each breadth area + 2 extras per depth area.
 * Both designations can be satisfied simultaneously by appropriate elective choices.
 */

import type { ProfileResponse } from '$lib/types/profile';

export interface DesignationResult {
	label: string;
	ce: boolean;
	ee: boolean;
}

export function computeDesignation(p: ProfileResponse): DesignationResult | null {
	let fromComputerAreas = 0;
	let fromElectricalAreas = 0;

	const bucketAreas = p.constraint_diagnostics?.requirement_buckets?.kernel_depth_by_area;

	if (bucketAreas && bucketAreas.length > 0) {
		for (const row of bucketAreas) {
			const count = row.course_codes?.length ?? 0;
			if (row.area >= 5 && row.area <= 6) fromComputerAreas += count;
			else if (row.area >= 1 && row.area <= 4) fromElectricalAreas += count;
		}
	} else {
		// Fallback: estimate from kernel/depth area metadata.
		// Each depth area contributes min_courses_per_depth_area (3) courses; breadth-only = 1.
		const depthSet = new Set(p.depth_areas_selected ?? []);
		for (const area of p.kernel_areas_selected ?? []) {
			const count = depthSet.has(area) ? 3 : 1;
			if (area >= 5 && area <= 6) fromComputerAreas += count;
			else if (area >= 1 && area <= 4) fromElectricalAreas += count;
		}
	}

	const ce = fromComputerAreas >= 4;
	const ee = fromElectricalAreas >= 5;
	if (!ce && !ee) return null;

	let label = '';
	if (ce && ee) label = 'CE / EE';
	else if (ce) label = 'CE';
	else label = 'EE';

	return { label, ce, ee };
}

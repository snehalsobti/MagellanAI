import { env } from '$env/dynamic/public';
import type { CourseInfo } from '$lib/types/profile';

const API_BASE_URL = env.PUBLIC_API_BASE_URL || 'http://localhost:8000';

export type CourseSearchFilters = {
	q?: string;
	term?: string;
	area?: number;
	kernel_course?: boolean;
	technical_elective?: boolean;
	free_elective?: boolean;
	course_type?: string;
	non_technical_type?: string;
	min_math?: number;
	min_ns?: number;
	min_cs?: number;
	min_es?: number;
	min_ed?: number;
	limit?: number;
};

export type ProgramConstraints = {
	total_num_credits: number;
	slots_per_term: number;
	capstone_codes: string[];
	min_breadth_areas: number;
	min_depth_areas: number;
	min_courses_per_depth_area: number;
	min_math_sci_courses: number;
	min_technical_elective_courses: number;
	min_complementary_courses: number;
	min_hss_in_complementary: number;
	min_free_elective_courses: number;
	max_csc34_credits: number;
	year3_min_technical_courses: number;
	year3_min_technical_courses_if_ece472: number;
	year12_default_choice: string;
	ceab_total_au: number;
	ceab_cs: number;
	ceab_math: number;
	ceab_ns: number;
	ceab_math_ns: number;
	ceab_es: number;
	ceab_ed: number;
	ceab_es_ed: number;
};

export async function fetchConstraints(): Promise<ProgramConstraints | null> {
	try {
		const response = await fetch(`${API_BASE_URL}/constraints`);
		if (!response.ok) return null;
		return (await response.json()) as ProgramConstraints;
	} catch {
		return null;
	}
}

export async function fetchYear12Courses(year12_choice: string): Promise<string[]> {
	const params = new URLSearchParams({ year12_choice });
	const response = await fetch(`${API_BASE_URL}/year12-courses?${params.toString()}`);
	if (!response.ok) return [];
	const data = (await response.json()) as { courses?: string[] };
	return data.courses || [];
}

export async function searchCourses(filters: CourseSearchFilters): Promise<CourseInfo[]> {
	const params = new URLSearchParams();
	for (const [key, value] of Object.entries(filters)) {
		if (value === undefined || value === null || value === '') continue;
		params.set(key, String(value));
	}
	const response = await fetch(`${API_BASE_URL}/courses?${params.toString()}`);
	if (!response.ok) {
		throw new Error('Failed to fetch course list.');
	}
	const data = (await response.json()) as { courses?: CourseInfo[] };
	return data.courses || [];
}

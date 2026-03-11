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

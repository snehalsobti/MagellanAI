export interface CourseInfo {
	course_code: string;
	course_name: string;
	course_description?: string | null;
	area: number;
	term?: string | null;
	num_credits: number;
	kernel_course: boolean;
	technical_elective: boolean;
	free_elective?: boolean;
	course_type?: string | null;
	non_technical_type?: string | null;
	ceab_math?: number | null;
	ceab_ns?: number | null;
	ceab_cs?: number | null;
	ceab_es?: number | null;
	ceab_ed?: number | null;
}

export interface SemesterPlanRow {
	term: string;
	course_codes: string[];
}

export interface CeabSummaryRow {
	label: string;
	required: number;
	achieved: number;
	delta: number;
	ok: boolean;
}

export interface ConstraintDiagnostics {
	ok: boolean;
	failed_checks: string[];
	ceab_failures: Array<{ label: string; deficit: number }>;
	ceab_summary?: CeabSummaryRow[];
	requirement_buckets?: {
		kernel_depth_by_area: Array<{ area: number; course_codes: string[] }>;
		engineering_economics: string[];
		capstone: string[];
		science_math: string[];
		technical_electives: string[];
		hss_cs: string[];
		free_elective: string[];
	};
}

export interface ProfileResponse {
	success: boolean;
	courses: CourseInfo[];
	semester_plan: SemesterPlanRow[];
	total_credits: number;
	kernel_areas_selected: number[];
	depth_areas_selected: number[];
	preferences_used: string[];
	preferences_skipped: string[];
	constraints_satisfied: boolean;
	generation_engine?: string | null;
	solver_runtime_ms?: number | null;
	preference_hit_count?: number | null;
	preference_weighted_score?: number | null;
	constraint_diagnostics?: ConstraintDiagnostics | null;
	error?: string | null;
}

export interface GenerateProfilePayload {
	interests: string;
	num_recommendations: number;
	year12_choice?: string | null;
}

export interface FeedbackPayload {
	locked: string[];
	excluded: string[];
	liked: string[];
	disliked: string[];
}

export interface RegenerateProfilePayload {
	interests?: string;
	num_recommendations?: number;
	year12_choice?: string | null;
	/** Original ranked preference list from the first /generate-profile call. */
	preferences: string[];
	feedback: FeedbackPayload;
}

export interface FeedbackHonorReport {
	liked_honored: string[];
	liked_skipped: string[];
	disliked_honored: string[];
	disliked_forced: string[];
}

/** Response from POST /regenerate-profile. Same shape as ProfileResponse but with extras. */
export interface RegenerateProfileResponse extends ProfileResponse {
	feedback_result?: FeedbackHonorReport | null;
	timed_out?: boolean;
	feedback_infeasible?: boolean;
}

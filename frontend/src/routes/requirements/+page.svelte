<script lang="ts">
	import { getAuthMode } from '$lib/auth';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { fetchConstraints } from '$lib/api/catalog';
	import type { ProgramConstraints } from '$lib/api/catalog';

	let constraints: ProgramConstraints | null = null;

	// Fallback display values matching the SSOT defaults — shown until the
	// API responds.  These must stay in sync with constraints.json if the
	// backend is unavailable; treat them as read-only compile-time constants.
	const FALLBACK: ProgramConstraints = {
		total_num_credits: 10.0, slots_per_term: 5,
		capstone_codes: ['ECE496Y1', 'APS490Y1', 'BME498Y1'],
		min_breadth_areas: 4, min_depth_areas: 2, min_courses_per_depth_area: 3,
		min_math_sci_courses: 1, min_technical_elective_courses: 3,
		min_complementary_courses: 4, min_hss_in_complementary: 2,
		min_free_elective_courses: 1, max_csc34_credits: 1.5,
		year3_min_technical_courses: 7, year3_min_technical_courses_if_ece472: 6,
		year12_default_choice: 'ECE297H1',
		ceab_total_au: 1870.0, ceab_cs: 240.0, ceab_math: 214.5, ceab_ns: 200.0,
		ceab_math_ns: 462.0, ceab_es: 247.5, ceab_ed: 247.5, ceab_es_ed: 990.0,
	};

	$: c = constraints ?? FALLBACK;

	$: programRequirements = [
		['Kernels', `${c.min_breadth_areas} courses from four different areas`],
		['Depths', `${c.min_depth_areas} courses in area X, with a chosen kernel course`],
		['Depths', `${c.min_depth_areas} courses in area Y, with a chosen kernel course`],
		['Engineering Economics', '1 (ECE472)'],
		['Capstone', 'Full year design project'],
		['Science/Math', `${c.min_math_sci_courses} course chosen from the Science/Math area`],
		['Technical Electives', `${c.min_technical_elective_courses} ECE technical areas`],
		['Free Elective', `${c.min_free_elective_courses}`],
		['Complementary Studies', `${c.min_complementary_courses}: ${c.min_hss_in_complementary} must be HSS courses`],
	];

	$: ceabRows = [[
		String(c.ceab_total_au),
		String(c.ceab_cs),
		String(c.ceab_math),
		String(c.ceab_ns),
		String(c.ceab_math_ns),
		String(c.ceab_es),
		String(c.ceab_ed),
		String(c.ceab_es_ed),
	]];

	const designationRows = [
		['E', 'E', 'E', 'E', 'E', 'E', 'EE'],
		['E', 'E', 'E', 'C', 'E', 'E', 'EE'],
		['E', 'E', 'E', 'C', 'E', 'C', 'EE'],
		['E', 'E', 'C', 'C', 'E', 'E', 'EE'],
		['E', 'E', 'C', 'C', 'E', 'C', 'CE'],
		['E', 'E', 'C', 'C', 'C', 'C', 'CE'],
	];

	onMount(async () => {
		if (!getAuthMode()) { goto('/signin'); return; }
		constraints = await fetchConstraints();
	});
</script>

<main class="page">
	<h2>ECE program requirements</h2>
	<div class="table-wrap">
		<table>
			<tbody>
				{#each programRequirements as row}
					<tr><th>{row[0]}</th><td>{row[1]}</td></tr>
				{/each}
			</tbody>
		</table>
	</div>

	<ul class="notes">
		<li>You must select ECE472. We will let you decide when you want to take this course.</li>
		<li>You have a choice between ECE496Y or APS490Y.</li>
		<li>
			You may select up to one technical elective from another department. However, if you select a
			course from another department you must seek approval from the ECE Undergraduate Office.
		</li>
		<li>
			Students not enrolled in the Computer Science Major or Specialist program at A&S, UTM, or UTSC, or the Data Science Specialist at A&S,
			are limited to a maximum of 1.5 credits in 300-/400-level CSC courses.
		</li>
		<li>
			For more details on approved HSS and CS courses, refer to
			<a href="https://undergrad.engineering.utoronto.ca/academics-registration/electives/humanities-social-science-hss-electives/">
				Approved HSS Course List
			</a>
			and
			<a href="https://undergrad.engineering.utoronto.ca/academics-registration/electives/complementary-studies-cs-electives/">
				Approved CS Course List
			</a>
		</li>
		<li>
			All pre-requisite/co-requisite requirements must be satisfied for your selection - this is not yet handled by MagellanAI
		</li>
	</ul>

	<h2>CEAB minimal course content component requirements</h2>
	<p>
		Canadian Engineering Accreditation Board (CEAB) provides engineers with the academic requirements
		necessary for registration as a professional engineer in Canada. To satisfy CEAB requirements, student
		must accumulate a minimum number of academic units (AU) in 7 categories: complementary studies (CS),
		mathematics (MAT), natural science (NAS), combined natural science and mathematics (NSM), engineering
		science (ENS), engineering design (DES), combined engineering science and design (ESD).
	</p>
	<div class="table-wrap">
		<table>
			<thead>
				<tr><th>AU</th><th>CS</th><th>MAT</th><th>NS</th><th>NSM</th><th>ENS</th><th>DES</th><th>ESD</th></tr>
			</thead>
			<tbody>
				{#each ceabRows as row}
					<tr>{#each row as col}<td>{col}</td>{/each}</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<h2>CE/EE Designation</h2>
	<p>
		Let E denote Areas 1-4 and let C denote Areas 5-6. The following table lists all six possible
		combinations. A profile may satisfy both EE and CE requirements.
	</p>
	<div class="table-wrap">
		<table>
			<thead>
				<tr>
					<th>Kernel</th><th>Kernel</th><th>Kernel</th><th>Kernel</th><th>Depth</th><th>Depth</th><th>Degree Designation</th>
				</tr>
			</thead>
			<tbody>
				{#each designationRows as row}
					<tr>{#each row as col}<td>{col}</td>{/each}</tr>
				{/each}
			</tbody>
		</table>
	</div>
</main>

<style>
	.page { max-width: 1100px; margin: 0 auto; padding: 26px 18px 42px; }
	h2 { margin: 20px 0 10px; }
	p, li { color: var(--text-muted); line-height: 1.55; }
	.table-wrap { overflow: auto; border: 1px solid var(--border); border-radius: 10px; background: white; }
	table { width: 100%; border-collapse: collapse; }
	th, td { border-bottom: 1px solid var(--border); padding: 10px 12px; text-align: left; }
	th { background: #f8faff; font-size: .82rem; text-transform: uppercase; letter-spacing: .2px; }
	.notes { margin: 12px 0; padding-left: 22px; }
</style>

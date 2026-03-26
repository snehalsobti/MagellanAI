<script lang="ts">
	import { onMount } from 'svelte';
	import { fetchConstraints } from '$lib/api/catalog';
	import type { ProgramConstraints } from '$lib/api/catalog';

	let constraints: ProgramConstraints | null = null;
	let loadError = false;

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
		{ label: 'Breadth (Kernels)',        value: `${c.min_breadth_areas} courses from four different technical areas` },
		{ label: 'Depth — Area X',           value: `${c.min_courses_per_depth_area} courses in a chosen area, including a kernel course` },
		{ label: 'Depth — Area Y',           value: `${c.min_courses_per_depth_area} courses in a second chosen area, including a kernel course` },
		{ label: 'Engineering Economics',    value: '1 required course (ECE472H1)' },
		{ label: 'Capstone Design Project',  value: `Full-year design project (${c.capstone_codes.join(', ')})` },
		{ label: 'Science / Mathematics',    value: `${c.min_math_sci_courses} course from the Science/Math area (Area 7)` },
		{ label: 'Technical Electives',      value: `${c.min_technical_elective_courses} courses from ECE technical areas` },
		{ label: 'Free Elective',            value: `${c.min_free_elective_courses} elective course` },
		{ label: 'Complementary Studies',    value: `${c.min_complementary_courses} total; at least ${c.min_hss_in_complementary} must be Humanities / Social Sciences` },
	];

	$: ceabHeaders = ['Total AU', 'CS', 'MAT', 'NS', 'NSM', 'ENS', 'DES', 'ESD'];
	$: ceabValues  = [
		String(c.ceab_total_au), String(c.ceab_cs), String(c.ceab_math),
		String(c.ceab_ns), String(c.ceab_math_ns), String(c.ceab_es),
		String(c.ceab_ed), String(c.ceab_es_ed),
	];

	const designationRules = [
		{
			designation: 'CE',
			badgeClass: 'badge-ce',
			condition: 'At least 4 of the 8 breadth+depth courses are from Areas 5–6 (Computer Engineering)'
		},
		{
			designation: 'EE',
			badgeClass: 'badge-ee',
			condition: 'At least 5 of the 8 breadth+depth courses are from Areas 1–4 (Electrical Engineering)'
		},
		{
			designation: 'CE / EE',
			badgeClass: 'badge-ceee',
			condition: 'Both CE and EE conditions are satisfied simultaneously (via appropriate elective choices)'
		}
	];

	onMount(async () => {
		// Server-side hooks.server.ts guards this route.
		const result = await fetchConstraints();
		if (result) {
			constraints = result;
		} else {
			loadError = true;
		}
	});
</script>

<svelte:head>
	<title>Program Charts — MagellanAI</title>
</svelte:head>

<main class="page">
	<!-- Page header -->
	<header class="page-header">
		<div>
			<div class="page-breadcrumb">Navigation Hub / Program Charts</div>
			<h1 class="page-title">Requirements & Regulations</h1>
			<p class="page-subtitle">ECE Program Requirements & Accreditation Standards · Program Charts</p>
		</div>
	</header>

	{#if loadError}
		<div class="notice notice-warn">
			⚠ Could not fetch live constraints from the backend — displaying default values.
		</div>
	{/if}

	<!-- Program Requirements -->
	<section class="section-card">
		<div class="section-header">
			<h2 class="section-title">
				<span class="section-icon" aria-hidden="true">📋</span>
				Program Requirements
			</h2>
			<p class="section-desc">Every generated profile must satisfy all of the following rules.</p>
		</div>
		<div class="table-wrap">
			<table class="data-table">
				<thead>
					<tr>
						<th>Requirement</th>
						<th>Specification</th>
					</tr>
				</thead>
				<tbody>
					{#each programRequirements as req}
						<tr>
							<th class="row-label">{req.label}</th>
							<td>{req.value}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</section>

	<!-- Notes -->
	<section class="section-card notes-section">
		<h2 class="section-title">
			<span class="section-icon" aria-hidden="true">⚓</span>
			Navigator's Notes
		</h2>
		<ul class="notes-list">
			<li>You must select <code>ECE472H1</code> (Engineering Economics). You may choose which semester to take it.</li>
			<li>You have a choice between <code>ECE496Y1</code> or <code>APS490Y1</code> for your capstone.</li>
			<li>
				You may select up to one technical elective from another department, subject to approval from the ECE Undergraduate Office.
			</li>
			<li>
				Students not enrolled in the CS Major, Specialist, or Data Science Specialist at A&S, UTM, or UTSC
				are limited to a maximum of <strong>{c.max_csc34_credits} credits</strong> in 300/400-level CSC courses.
			</li>
			<li>
				For approved elective lists, see the
				<a href="https://undergrad.engineering.utoronto.ca/academics-registration/electives/humanities-social-science-hss-electives/" target="_blank" rel="noopener">
					HSS Elective List
				</a>
				and
				<a href="https://undergrad.engineering.utoronto.ca/academics-registration/electives/complementary-studies-cs-electives/" target="_blank" rel="noopener">
					CS Elective List
				</a>.
			</li>
			<li>All prerequisite/co-requisite requirements must be satisfied — MagellanAI does not yet validate these.</li>
		</ul>
	</section>

	<!-- CEAB Requirements -->
	<section class="section-card">
		<div class="section-header">
			<h2 class="section-title">
				<span class="section-icon" aria-hidden="true">🌐</span>
				CEAB Academic Unit Requirements
			</h2>
			<p class="section-desc">
				The Canadian Engineering Accreditation Board (CEAB) requires a minimum number of Academic Units (AU)
				across seven categories. These ensure your degree qualifies for professional engineering registration in Canada.
			</p>
		</div>
		<div class="table-wrap">
			<table class="data-table ceab-table">
				<thead>
					<tr>
						{#each ceabHeaders as h}
							<th>{h}</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					<tr>
						{#each ceabValues as v}
							<td>{v}</td>
						{/each}
					</tr>
				</tbody>
			</table>
		</div>
		<div class="ceab-legend">
			<span><strong>CS</strong> = Complementary Studies</span>
			<span><strong>MAT</strong> = Mathematics</span>
			<span><strong>NS</strong> = Natural Science</span>
			<span><strong>NSM</strong> = Math + Natural Science</span>
			<span><strong>ENS</strong> = Engineering Science</span>
			<span><strong>DES</strong> = Engineering Design</span>
			<span><strong>ESD</strong> = Engineering Science + Design</span>
		</div>
	</section>

	<!-- CE/EE Designation -->
	<section class="section-card">
		<div class="section-header">
			<h2 class="section-title">
				<span class="section-icon" aria-hidden="true">🎓</span>
				CE / EE Degree Designation
			</h2>
			<p class="section-desc">
				The designation is determined by how many of your <strong>eight breadth+depth courses</strong>
				(four breadth kernels + four depth extras) fall in Computer vs Electrical areas.
				Areas&nbsp;1–4 are Electrical Engineering; Areas&nbsp;5–6 are Computer Engineering.
			</p>
		</div>
		<div class="table-wrap">
			<table class="data-table designation-table">
				<thead>
					<tr>
						<th class="designation-col">Designation</th>
						<th>Condition (among the 8 breadth+depth courses)</th>
					</tr>
				</thead>
				<tbody>
					{#each designationRules as rule}
						<tr>
							<td class="designation-badge">
								<span class="badge {rule.badgeClass}">{rule.designation}</span>
							</td>
							<td>{rule.condition}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		<p class="designation-note">
			The eight courses are: one kernel from each of the four breadth areas, plus two additional courses
			from each of the two depth areas. By appropriate choice of kernel courses as technical or free
			electives, it may be possible to satisfy both CE and EE requirements simultaneously.
			MagellanAI displays your designation in real time on the Generate page.
		</p>
	</section>
</main>

<style>
	/* ── Page ─────────────────────────────────────────────────────────────────── */
	.page {
		max-width: 1100px;
		margin: 0 auto;
		padding: 28px 24px 60px;
		display: grid;
		gap: 22px;
	}

	/* ── Page header ─────────────────────────────────────────────────────────── */
	.page-header {
		animation: fade-in 0.45s ease;
	}
	.page-breadcrumb {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.65rem;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--text-faint);
		margin-bottom: 8px;
	}
	.page-title {
		font-family: 'Cinzel', serif;
		font-size: 1.7rem;
		font-weight: 700;
		color: var(--gold);
		letter-spacing: 0.06em;
		margin: 0 0 6px;
	}
	.page-subtitle {
		font-size: 0.85rem;
		color: var(--text-muted);
		margin: 0;
		letter-spacing: 0.04em;
	}

	/* ── Section card ────────────────────────────────────────────────────────── */
	.section-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow: hidden;
		box-shadow: var(--shadow-sm);
	}

	.section-header {
		padding: 20px 20px 0;
	}

	.section-title {
		font-family: 'Cinzel', serif;
		font-size: 1.05rem;
		font-weight: 600;
		letter-spacing: 0.05em;
		color: var(--text);
		margin: 0 0 6px;
		display: flex;
		align-items: center;
		gap: 10px;
	}
	.section-icon { font-size: 1rem; }

	.section-desc {
		font-size: 0.9rem;
		color: var(--text-muted);
		margin: 0 0 16px;
		line-height: 1.6;
	}

	/* ── Table ───────────────────────────────────────────────────────────────── */
	.table-wrap {
		overflow-x: auto;
	}

	.data-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.9rem;
	}

	.data-table th,
	.data-table td {
		border-bottom: 1px solid var(--border);
		padding: 11px 16px;
		text-align: left;
		vertical-align: top;
	}

	.data-table thead th {
		background: var(--surface-raised);
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.75rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-muted);
		font-weight: 500;
		border-bottom: 2px solid var(--border);
	}

	.data-table tbody tr:last-child td,
	.data-table tbody tr:last-child th {
		border-bottom: none;
	}

	.data-table tbody tr:hover td,
	.data-table tbody tr:hover th {
		background: var(--surface-soft);
	}

	.row-label {
		font-weight: 600;
		color: var(--gold);
		font-size: 0.88rem;
		width: 220px;
		white-space: nowrap;
	}

	/* ── CEAB table ──────────────────────────────────────────────────────────── */
	.ceab-table th,
	.ceab-table td {
		text-align: center;
		width: auto;
	}

	.ceab-legend {
		display: flex;
		flex-wrap: wrap;
		gap: 8px 16px;
		padding: 14px 18px;
		border-top: 1px solid var(--border-soft);
		background: var(--surface-soft);
	}
	.ceab-legend span {
		font-size: 0.75rem;
		color: var(--text-muted);
	}
	.ceab-legend strong {
		color: var(--text);
	}

	/* ── Designation table ───────────────────────────────────────────────────── */
	.designation-table th,
	.designation-table td {
		text-align: left;
	}
	.designation-col {
		background: var(--surface-raised) !important;
		width: 130px;
		white-space: nowrap;
	}

	.designation-badge { text-align: center; width: 130px; }
	.badge {
		display: inline-block;
		font-family: 'Cinzel', serif;
		font-size: 0.75rem;
		font-weight: 700;
		letter-spacing: 0.08em;
		padding: 3px 10px;
		border-radius: 999px;
		border: 1.5px solid;
	}
	.badge-ee {
		background: rgba(32, 119, 178, 0.12);
		border-color: var(--ocean);
		color: var(--ocean-light);
	}
	.badge-ce {
		background: rgba(201, 168, 76, 0.1);
		border-color: var(--gold-dim);
		color: var(--gold);
	}
	.badge-ceee {
		background: var(--surface-raised);
		border-color: var(--border);
		color: var(--text-muted);
	}

	.designation-note {
		font-size: 0.82rem;
		color: var(--text-muted);
		line-height: 1.65;
		padding: 12px 20px 16px;
		margin: 0;
		border-top: 1px solid var(--border-soft);
	}

	/* ── Notes ───────────────────────────────────────────────────────────────── */
	.notes-section { padding: 20px; }
	.notes-list {
		margin: 12px 0 0;
		padding-left: 20px;
		display: grid;
		gap: 8px;
	}
	.notes-list li {
		font-size: 0.85rem;
		color: var(--text-muted);
		line-height: 1.6;
	}
	.notes-list code {
		font-family: 'JetBrains Mono', monospace;
		background: var(--surface-raised);
		border: 1px solid var(--border);
		border-radius: 4px;
		padding: 1px 5px;
		font-size: 0.82rem;
		color: var(--ocean-bright);
	}

	.notice {
		border-radius: var(--radius-sm);
		padding: 10px 14px;
		font-size: 0.84rem;
		border: 1px solid;
	}
	.notice-warn { background: var(--warn-bg); border-color: var(--warn-border); color: var(--warn-text); }

	/* ── Responsive ──────────────────────────────────────────────────────────── */
	@media (max-width: 700px) {
		.page { padding: 18px 14px 40px; }
		.row-label { width: auto; white-space: normal; }
	}
</style>

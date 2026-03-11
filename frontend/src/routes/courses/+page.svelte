<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { getAuthMode } from '$lib/auth';
	import { searchCourses, type CourseSearchFilters } from '$lib/api/catalog';
	import type { CourseInfo } from '$lib/types/profile';
	import CourseDetailsModal from '$lib/components/CourseDetailsModal.svelte';

	let loading = false;
	let error = '';
	let rows: CourseInfo[] = [];
	let selected: CourseInfo | null = null;

	let q = '';
	let term = '';
	let area = '';
	let kernel = '';
	let technical = '';
	let free = '';
	let courseType = '';
	let nonTech = '';
	let min_math = '';
	let min_ns = '';
	let min_cs = '';
	let min_es = '';
	let min_ed = '';

	onMount(async () => {
		if (!getAuthMode()) {
			goto('/signin');
			return;
		}
		await runSearch();
	});

	function boolOrUndef(v: string): boolean | undefined {
		if (v === 'true') return true;
		if (v === 'false') return false;
		return undefined;
	}

	function formatCourseType(v: string | null | undefined): string {
		if (!v) return '-';
		const normalized = v.replace('_', '-').toLowerCase();
		return normalized.charAt(0).toUpperCase() + normalized.slice(1);
	}

	function formatNonTech(v: string | null | undefined): string {
		if (!v) return '-';
		const n = v.toLowerCase();
		if (n === 'hss') return 'HSS';
		if (n === 'cs') return 'CS';
		return n.charAt(0).toUpperCase() + n.slice(1);
	}

	async function runSearch() {
		loading = true;
		error = '';
		try {
			const filters: CourseSearchFilters = {
				q,
				term: term || undefined,
				area: area ? Number(area) : undefined,
				kernel_course: boolOrUndef(kernel),
				technical_elective: boolOrUndef(technical),
				free_elective: boolOrUndef(free),
				course_type: courseType || undefined,
				non_technical_type: nonTech || undefined,
				min_math: min_math ? Number(min_math) : undefined,
				min_ns: min_ns ? Number(min_ns) : undefined,
				min_cs: min_cs ? Number(min_cs) : undefined,
				min_es: min_es ? Number(min_es) : undefined,
				min_ed: min_ed ? Number(min_ed) : undefined,
				limit: 1000
			};
			rows = await searchCourses(filters);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to fetch courses.';
		} finally {
			loading = false;
		}
	}
</script>

<main class="page">
	<section class="filters">
		<h2>Course list search</h2>
		<div class="grid">
			<input bind:value={q} placeholder="Search by code, name, description" />
			<select bind:value={term}><option value="">Any term</option><option>F</option><option>S</option><option>Y</option></select>
			<input bind:value={area} placeholder="Area (e.g., 5)" />
			<select bind:value={kernel}><option value="">Kernel: Any</option><option value="true">Kernel: Yes</option><option value="false">Kernel: No</option></select>
			<select bind:value={technical}><option value="">Tech elective: Any</option><option value="true">Yes</option><option value="false">No</option></select>
			<select bind:value={free}><option value="">Free elective: Any</option><option value="true">Yes</option><option value="false">No</option></select>
			<select bind:value={courseType}><option value="">Course type: Any</option><option value="technical">Technical</option><option value="non_technical">Non-technical</option></select>
			<select bind:value={nonTech}><option value="">Non-tech type: Any</option><option value="hss">HSS</option><option value="cs">CS</option><option value="other">Other</option></select>
			<input bind:value={min_math} placeholder="Min Math" />
			<input bind:value={min_ns} placeholder="Min NS" />
			<input bind:value={min_cs} placeholder="Min CS" />
			<input bind:value={min_es} placeholder="Min ES" />
			<input bind:value={min_ed} placeholder="Min ED" />
		</div>
		<button type="button" on:click={runSearch} disabled={loading}>{loading ? 'Searching...' : 'Search courses'}</button>
	</section>

	<section class="table-wrap">
		{#if error}<p class="error">{error}</p>{/if}
		<table>
			<thead>
				<tr><th>Code</th><th>Name</th><th>Term</th><th>Area</th><th>Type</th><th>HSS/CS</th><th>Kernel</th></tr>
			</thead>
			<tbody>
				{#each rows as row}
					<tr on:click={() => (selected = row)}>
						<td>{row.course_code}</td>
						<td>{row.course_name}</td>
						<td>{row.term || '-'}</td>
						<td>{row.area === -1 ? '-' : row.area}</td>
						<td>{formatCourseType(row.course_type)}</td>
						<td>{formatNonTech(row.non_technical_type)}</td>
						<td>{row.kernel_course ? 'Y' : 'N'}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</section>

	<CourseDetailsModal course={selected} onClose={() => (selected = null)} />
</main>

<style>
	.page { max-width: 1200px; margin: 0 auto; padding: 20px 18px 32px; display:grid; gap: 12px; }
	.filters, .table-wrap { background: #fff; border: 1px solid var(--border); border-radius: 12px; box-shadow: var(--shadow-sm); padding: 14px; }
	h2 { margin: 0 0 10px; }
	.grid { display:grid; gap: 8px; grid-template-columns: repeat(4,minmax(0,1fr)); margin-bottom: 10px; }
	input, select { border:1px solid var(--border); border-radius: 8px; padding: 8px 10px; font: inherit; }
	button { border: 0; border-radius: 10px; padding: 10px 14px; background: #2563eb; color: #fff; cursor: pointer; }
	table { width: 100%; border-collapse: collapse; }
	th, td { padding: 9px 10px; border-bottom: 1px solid var(--border); text-align: left; font-size: .84rem; }
	th { background: #f8faff; font-size: .76rem; text-transform: uppercase; letter-spacing: .2px; }
	tr:hover td { background: #f3f7ff; cursor: pointer; }
	.error { color: #b42318; }
	@media (max-width: 1000px){ .grid { grid-template-columns: repeat(2,minmax(0,1fr)); } }
</style>

<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
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
		// Server-side hooks.server.ts guards this route.
		await runSearch();
	});

	function boolOrUndef(v: string): boolean | undefined {
		if (v === 'true') return true;
		if (v === 'false') return false;
		return undefined;
	}

	function formatCourseType(v: string | null | undefined): string {
		if (!v) return '—';
		return v.replace('_', '-').replace(/^\w/, c => c.toUpperCase());
	}

	function formatNonTech(v: string | null | undefined): string {
		if (!v) return '—';
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

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') runSearch();
	}
</script>

<svelte:head>
	<title>Course Catalog — MagellanAI</title>
</svelte:head>

<main class="page">
	<!-- Header -->
	<header class="page-header">
		<div class="page-breadcrumb">Navigation Hub / Course Catalog</div>
		<h1 class="page-title">Course Catalog</h1>
		<p class="page-subtitle">Search and filter the full ECE course catalog · Ship's Manifest</p>
	</header>

	<!-- Filter panel -->
	<section class="filter-panel">
		<div class="filter-header">
			<h2 class="filter-title">
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
					<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
				</svg>
				Filter Courses
			</h2>
			<span class="result-count">
				{#if loading}
					Searching…
				{:else}
					{rows.length} course{rows.length !== 1 ? 's' : ''} found
				{/if}
			</span>
		</div>

		<div class="filter-grid">
			<div class="filter-field filter-wide">
				<label for="q-input" class="filter-label">Search</label>
				<div class="input-with-icon">
					<svg class="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
						<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
					</svg>
					<input
						id="q-input"
						bind:value={q}
						placeholder="Code, name, or description…"
						onkeydown={handleKeydown}
					/>
				</div>
			</div>

			<div class="filter-field">
				<label for="term-sel" class="filter-label">Term</label>
				<select id="term-sel" bind:value={term}>
					<option value="">Any term</option>
					<option>F</option>
					<option>S</option>
					<option>Y</option>
				</select>
			</div>

			<div class="filter-field">
				<label for="area-input" class="filter-label">Area</label>
				<input id="area-input" bind:value={area} placeholder="e.g. 5" onkeydown={handleKeydown} />
			</div>

			<div class="filter-field">
				<label for="kernel-sel" class="filter-label">Kernel</label>
				<select id="kernel-sel" bind:value={kernel}>
					<option value="">Any</option>
					<option value="true">Yes</option>
					<option value="false">No</option>
				</select>
			</div>

			<div class="filter-field">
				<label for="tech-sel" class="filter-label">Tech Elective</label>
				<select id="tech-sel" bind:value={technical}>
					<option value="">Any</option>
					<option value="true">Yes</option>
					<option value="false">No</option>
				</select>
			</div>

			<div class="filter-field">
				<label for="free-sel" class="filter-label">Free Elective</label>
				<select id="free-sel" bind:value={free}>
					<option value="">Any</option>
					<option value="true">Yes</option>
					<option value="false">No</option>
				</select>
			</div>

			<div class="filter-field">
				<label for="type-sel" class="filter-label">Course Type</label>
				<select id="type-sel" bind:value={courseType}>
					<option value="">Any type</option>
					<option value="technical">Technical</option>
					<option value="non_technical">Non-technical</option>
				</select>
			</div>

			<div class="filter-field">
				<label for="nontech-sel" class="filter-label">Non-tech Type</label>
				<select id="nontech-sel" bind:value={nonTech}>
					<option value="">Any</option>
					<option value="hss">HSS</option>
					<option value="cs">CS</option>
					<option value="other">Other</option>
				</select>
			</div>
		</div>

		<!-- CEAB filters -->
		<details class="ceab-filters">
			<summary class="ceab-summary">
				<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
					<polyline points="9 18 15 12 9 6"/>
				</svg>
				CEAB Minimum Filters
			</summary>
			<div class="ceab-grid">
				{#each [['min_math', 'Min Math (AU)', 'min_math'], ['min_ns', 'Min NS (AU)', 'min_ns'], ['min_cs', 'Min CS (AU)', 'min_cs'], ['min_es', 'Min ES (AU)', 'min_es'], ['min_ed', 'Min ED (AU)', 'min_ed']] as [varName, label]}
					<div class="filter-field">
						<label for="{varName}-input" class="filter-label">{label}</label>
						{#if varName === 'min_math'}
							<input id="{varName}-input" bind:value={min_math} placeholder="0" onkeydown={handleKeydown} />
						{:else if varName === 'min_ns'}
							<input id="{varName}-input" bind:value={min_ns} placeholder="0" onkeydown={handleKeydown} />
						{:else if varName === 'min_cs'}
							<input id="{varName}-input" bind:value={min_cs} placeholder="0" onkeydown={handleKeydown} />
						{:else if varName === 'min_es'}
							<input id="{varName}-input" bind:value={min_es} placeholder="0" onkeydown={handleKeydown} />
						{:else if varName === 'min_ed'}
							<input id="{varName}-input" bind:value={min_ed} placeholder="0" onkeydown={handleKeydown} />
						{/if}
					</div>
				{/each}
			</div>
		</details>

		<div class="filter-actions">
			<button type="button" class="btn-search" onclick={runSearch} disabled={loading}>
				{#if loading}
					<div class="spinner-compass sm" aria-hidden="true"></div>
					Searching…
				{:else}
					<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
						<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
					</svg>
					Search Courses
				{/if}
			</button>
		</div>
	</section>

	<!-- Results table -->
	<section class="results-panel">
		{#if error}
			<div class="notice notice-danger">{error}</div>
		{/if}

		{#if loading && rows.length === 0}
			<div class="loading-state">
				<div class="spinner-compass" aria-hidden="true"></div>
				<span>Searching the catalog…</span>
			</div>
		{:else if rows.length === 0 && !loading}
			<div class="empty-state">
				<span class="empty-icon" aria-hidden="true">⚓</span>
				<p>No courses found matching your filters.</p>
			</div>
		{:else}
			<div class="table-wrap">
				<table class="data-table">
					<thead>
						<tr>
							<th>Code</th>
							<th>Course Name</th>
							<th>Term</th>
							<th>Area</th>
							<th>Type</th>
							<th>HSS/CS</th>
							<th>Kernel</th>
						</tr>
					</thead>
					<tbody>
						{#each rows as row}
							<tr onclick={() => (selected = row)} class="row-clickable">
								<td class="code-cell">
									<code>{row.course_code}</code>
								</td>
								<td class="name-cell">{row.course_name}</td>
								<td class="center-cell">
									{#if row.term}
										<span class="term-badge term-{(row.term || '').toLowerCase()}">{row.term}</span>
									{:else}
										<span class="muted">—</span>
									{/if}
								</td>
								<td class="center-cell">
									{#if row.area !== -1}
										<span class="area-badge">Area {row.area}</span>
									{:else}
										<span class="muted">—</span>
									{/if}
								</td>
								<td>{formatCourseType(row.course_type)}</td>
								<td>{formatNonTech(row.non_technical_type)}</td>
								<td class="center-cell">
									{#if row.kernel_course}
										<span class="kernel-yes" title="Kernel course">✦</span>
									{:else}
										<span class="muted">—</span>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
			{#if rows.length >= 1000}
				<p class="table-footer-note">Showing first 1,000 results. Use filters to narrow your search.</p>
			{/if}
		{/if}
	</section>

	<CourseDetailsModal course={selected} onClose={() => (selected = null)} />
</main>

<style>
	/* ── Page ─────────────────────────────────────────────────────────────────── */
	.page {
		max-width: 1200px;
		margin: 0 auto;
		padding: 28px 24px 60px;
		display: grid;
		gap: 18px;
	}

	/* ── Page header ─────────────────────────────────────────────────────────── */
	.page-breadcrumb {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.65rem;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--text-faint);
		margin-bottom: 6px;
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
	}

	/* ── Filter panel ─────────────────────────────────────────────────────────── */
	.filter-panel {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 18px 20px;
		box-shadow: var(--shadow-sm);
	}

	.filter-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 16px;
		gap: 8px;
		flex-wrap: wrap;
	}

	.filter-title {
		display: flex;
		align-items: center;
		gap: 8px;
		font-family: 'Cinzel', serif;
		font-size: 0.95rem;
		font-weight: 600;
		color: var(--text);
		margin: 0;
		letter-spacing: 0.04em;
	}

	.result-count {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.77rem;
		color: var(--text-muted);
		letter-spacing: 0.06em;
	}

	.filter-grid {
		display: grid;
		gap: 10px;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		margin-bottom: 12px;
	}

	.filter-wide { grid-column: span 2; }

	.filter-field {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.filter-label {
		font-size: 0.75rem;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-muted);
		cursor: default;
	}

	.input-with-icon {
		position: relative;
	}
	.search-icon {
		position: absolute;
		left: 10px;
		top: 50%;
		transform: translateY(-50%);
		color: var(--text-faint);
		pointer-events: none;
	}
	.input-with-icon input {
		padding-left: 32px;
	}

	input, select {
		background: var(--surface-raised);
		color: var(--text);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 8px 10px;
		font-size: 0.9rem;
		font-family: 'Raleway', sans-serif;
		width: 100%;
		transition: border-color 0.18s, box-shadow 0.18s;
	}
	input:focus, select:focus {
		outline: none;
		border-color: var(--ocean-light);
		box-shadow: 0 0 0 3px rgba(32, 119, 178, 0.18);
	}
	input::placeholder { color: var(--text-faint); }

	/* ── CEAB filters ─────────────────────────────────────────────────────────── */
	.ceab-filters {
		border-top: 1px solid var(--border-soft);
		padding-top: 12px;
		margin-bottom: 12px;
	}
	.ceab-summary {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 0.78rem;
		font-weight: 600;
		color: var(--text-muted);
		letter-spacing: 0.06em;
		cursor: pointer;
		list-style: none;
		user-select: none;
		transition: color 0.15s;
	}
	.ceab-summary::-webkit-details-marker { display: none; }
	.ceab-summary:hover { color: var(--text); }
	.ceab-summary svg { transition: transform 0.2s; }
	details[open] .ceab-summary svg { transform: rotate(90deg); }

	.ceab-grid {
		display: grid;
		grid-template-columns: repeat(5, minmax(0, 1fr));
		gap: 10px;
		margin-top: 12px;
	}

	/* ── Filter actions ───────────────────────────────────────────────────────── */
	.filter-actions {
		display: flex;
		justify-content: flex-end;
	}

	.btn-search {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 9px 18px;
		border-radius: 10px;
		border: 1px solid var(--ocean);
		background: linear-gradient(135deg, rgba(32, 119, 178, 0.2), rgba(32, 119, 178, 0.1));
		color: var(--ocean-bright);
		font-size: 0.84rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.18s ease;
		font-family: 'Raleway', sans-serif;
	}
	.btn-search:hover:not(:disabled) {
		background: rgba(32, 119, 178, 0.25);
		border-color: var(--ocean-light);
		box-shadow: var(--glow-ocean);
		transform: translateY(-1px);
	}
	.btn-search:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	/* ── Results ──────────────────────────────────────────────────────────────── */
	.results-panel {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow: hidden;
		box-shadow: var(--shadow-sm);
	}

	.loading-state,
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 12px;
		padding: 60px 20px;
		color: var(--text-muted);
		font-size: 0.88rem;
	}
	.empty-icon { font-size: 2rem; opacity: 0.3; }

	.table-wrap { overflow-x: auto; }

	.data-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.9rem;
	}
	.data-table th {
		background: var(--surface-raised);
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.73rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-muted);
		font-weight: 500;
		padding: 10px 14px;
		border-bottom: 2px solid var(--border);
		text-align: left;
		white-space: nowrap;
	}
	.data-table td {
		padding: 9px 14px;
		border-bottom: 1px solid var(--border-soft);
		color: var(--text);
		vertical-align: middle;
	}
	.data-table tbody tr:last-child td { border-bottom: none; }

	.row-clickable { cursor: pointer; transition: background 0.12s; }
	.row-clickable:hover td { background: var(--surface-hover); }

	.code-cell code {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.88rem;
		color: var(--ocean-bright);
		background: rgba(32, 119, 178, 0.1);
		border: 1px solid rgba(32, 119, 178, 0.2);
		border-radius: 4px;
		padding: 2px 6px;
	}

	.name-cell { font-weight: 500; }

	.center-cell { text-align: center; }

	.term-badge {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.77rem;
		font-weight: 600;
		padding: 2px 8px;
		border-radius: 999px;
		border: 1px solid;
	}
	.term-f { background: rgba(32, 119, 178, 0.1);  border-color: rgba(32, 119, 178, 0.3);  color: var(--ocean-bright); }
	.term-s { background: rgba(201, 168, 76, 0.1);  border-color: rgba(201, 168, 76, 0.3);  color: var(--gold); }
	.term-y { background: rgba(94, 207, 138, 0.1);  border-color: rgba(94, 207, 138, 0.3);  color: var(--success-text); }

	.area-badge {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.76rem;
		padding: 2px 7px;
		border-radius: 4px;
		background: var(--surface-raised);
		border: 1px solid var(--border);
		color: var(--text-muted);
	}

	.kernel-yes {
		color: var(--gold);
		font-size: 0.9rem;
	}

	.muted { color: var(--text-faint); }

	.table-footer-note {
		font-size: 0.75rem;
		color: var(--text-faint);
		text-align: center;
		padding: 10px;
		border-top: 1px solid var(--border-soft);
		margin: 0;
	}

	.notice {
		margin: 12px;
		border-radius: var(--radius-sm);
		padding: 10px 14px;
		font-size: 0.84rem;
		border: 1px solid;
	}
	.notice-danger { background: var(--danger-bg); border-color: var(--danger-border); color: var(--danger-text); }

	/* ── Responsive ──────────────────────────────────────────────────────────── */
	@media (max-width: 1000px) {
		.filter-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
		.filter-wide { grid-column: span 2; }
		.ceab-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
	}
	@media (max-width: 600px) {
		.filter-grid { grid-template-columns: 1fr; }
		.filter-wide { grid-column: span 1; }
		.ceab-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
	}
</style>

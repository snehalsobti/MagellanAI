<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { getAuthMode } from '$lib/auth';
	import { fetchYear12Courses } from '$lib/api/catalog';
	import { generateProfile } from '$lib/api/profile';
	import CourseDetailsModal from '$lib/components/CourseDetailsModal.svelte';
	import type { CourseInfo, ProfileResponse } from '$lib/types/profile';

	const terms = ['3F', '3S', '4F', '4S'];

	let interests = '';
	let loading = false;
	let profile: ProfileResponse | null = null;
	let error: string | null = null;
	let selectedCourse: CourseInfo | null = null;
	let year12Choice: 'ECE295H1' | 'ECE297H1' = 'ECE297H1';
	let year12Courses: string[] = [];
	let loadingTimer: ReturnType<typeof setInterval> | null = null;
let elapsedSeconds = 0;
let loadingDots = '.';

	onMount(async () => {
		if (!getAuthMode()) {
			goto('/signin');
			return;
		}
		await refreshYear12Courses();
	});

	async function refreshYear12Courses() {
		year12Courses = await fetchYear12Courses(year12Choice);
	}

	$: year12Choice, refreshYear12Courses();

	function courseLevel(code: string): number | null {
		const m = code.match(/(\d{3})/);
		if (!m) return null;
		return Number(m[1].charAt(0));
	}

	function cycleLoadingSteps() {
		if (loadingTimer) clearInterval(loadingTimer);
		loadingTimer = setInterval(() => {
		elapsedSeconds = Number((elapsedSeconds + 0.5).toFixed(1));
		loadingDots = loadingDots.length >= 3 ? '.' : `${loadingDots}.`;
	}, 500);
	}

	function stopLoadingSteps() {
		if (loadingTimer) clearInterval(loadingTimer);
		loadingTimer = null;
	elapsedSeconds = 0;
	loadingDots = '.';
	}

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		if (!interests.trim()) {
			error = 'Please enter your interests.';
			return;
		}
		loading = true;
		error = null;
		profile = null;
		elapsedSeconds = 0;
		loadingDots = '.';
		cycleLoadingSteps();
		try {
			profile = await generateProfile({
				interests: interests.trim(),
				num_recommendations: 15,
				year12_choice: year12Choice
			});
		} catch (e) {
			error =
				e instanceof Error
					? e.message
					: 'Failed to generate profile. Make sure backend is running and configured.';
		} finally {
			loading = false;
			stopLoadingSteps();
		}
	}

	function sumSemesterSlots(current: ProfileResponse): number {
		return current.semester_plan?.reduce((acc, row) => acc + (row.course_codes?.length || 0), 0) ?? 0;
	}

	function courseMap(current: ProfileResponse): Map<string, CourseInfo> {
		return new Map(current.courses.map((c) => [c.course_code, c]));
	}

	function openCourseByCode(code: string) {
		if (!profile) return;
		selectedCourse = courseMap(profile).get(code) || null;
	}

	function uniqueByCode(courses: CourseInfo[]) {
		return Array.from(new Map(courses.map((c) => [c.course_code, c])).values());
	}

	function computeProgramBuckets(current: ProfileResponse) {
		const all = uniqueByCode(current.courses);
		const byCode = new Map(all.map((c) => [c.course_code, c]));
		const diagBuckets = current.constraint_diagnostics?.requirement_buckets;
		if (diagBuckets) {
			const areaRows = new Map<number, CourseInfo[]>();
			for (const row of diagBuckets.kernel_depth_by_area || []) {
				const courses = (row.course_codes || [])
					.map((code) => byCode.get(code))
					.filter((c): c is CourseInfo => Boolean(c))
					.sort((a, b) => a.course_code.localeCompare(b.course_code));
				areaRows.set(row.area, courses);
			}
			const pickCodes = (codes: string[]) =>
				(codes || [])
					.map((code) => byCode.get(code))
					.filter((c): c is CourseInfo => Boolean(c));
			return {
				areaRows,
				engEcon: pickCodes(diagBuckets.engineering_economics),
				capstone: pickCodes(diagBuckets.capstone),
				sciMath: pickCodes(diagBuckets.science_math),
				technicalElectives: pickCodes(diagBuckets.technical_electives),
				hsscs: pickCodes(diagBuckets.hss_cs),
				free: pickCodes(diagBuckets.free_elective),
				byCode
			};
		}

		const areaRows = new Map<number, CourseInfo[]>();
		const kernelDepthCodes = new Set<string>();
		for (const c of all.filter((c) => c.area >= 1 && c.area <= 6)) {
			if (!areaRows.has(c.area)) areaRows.set(c.area, []);
			areaRows.get(c.area)?.push(c);
			kernelDepthCodes.add(c.course_code);
		}
		for (const [area, courses] of areaRows.entries()) {
			areaRows.set(
				area,
				courses
					.slice()
					.sort((a, b) => a.course_code.localeCompare(b.course_code))
			);
		}

		// Outside kernel/depth, each course is consumed by at most one requirement bucket.
		const consumed = new Set<string>(kernelDepthCodes);
		const pick = (predicate: (c: CourseInfo) => boolean, limit: number): CourseInfo[] => {
			const picked: CourseInfo[] = [];
			for (const c of all) {
				if (picked.length >= limit) break;
				if (consumed.has(c.course_code)) continue;
				if (!predicate(c)) continue;
				picked.push(c);
				consumed.add(c.course_code);
			}
			return picked;
		};

		const engEcon = pick((c) => c.course_code === 'ECE472H1', 1);
		const capstone = pick((c) => ['ECE496Y1', 'APS490Y1', 'BME498Y1'].includes(c.course_code), 1);
		const sciMath = pick((c) => c.area === 7, 1);
		const technicalElectives = pick(
			(c) => c.technical_elective && c.course_code !== 'ECE472H1',
			3
		);
		const hsscs = pick((c) => ['hss', 'cs'].includes((c.non_technical_type || '').toLowerCase()), 4);
		const free = pick((c) => Boolean(c.free_elective), 1);

		return { areaRows, engEcon, capstone, sciMath, technicalElectives, hsscs, free, byCode };
	}

	$: mapped = profile ? courseMap(profile) : new Map<string, CourseInfo>();
	$: buckets = profile ? computeProgramBuckets(profile) : null;
	$: year1Courses = year12Courses.filter((c) => courseLevel(c) === 1);
	$: year2Courses = year12Courses.filter(
		(c) => courseLevel(c) === 2 && c !== 'ECE295H1' && c !== 'ECE297H1'
	);
	$: otherCourses = year12Courses.filter((c) => {
		const lvl = courseLevel(c);
		return lvl !== 1 && lvl !== 2 && c !== 'ECE295H1' && c !== 'ECE297H1';
	});
</script>

<svelte:head><title>Generate Profile - MagellanAI</title></svelte:head>

<main class="page">
	<section class="prompt-panel">
		<h2>Generate a new course profile</h2>
		<p>
			Describe your academic interests and goals. MagellanAI will rank relevant courses, generate a valid
			profile, and verify constraints.
		</p>
		<form on:submit={handleSubmit}>
			<fieldset class="choice-fieldset">
				<legend>Choose your Year 2 Design Course</legend>
			<div class="radio-row">
				<label><input type="radio" bind:group={year12Choice} value="ECE295H1" /> ECE295H1</label>
				<label><input type="radio" bind:group={year12Choice} value="ECE297H1" /> ECE297H1</label>
			</div>
			</fieldset>

			<div class="year12-list">
				<h3>Year 1/2 courses currently considered</h3>
				<div class="year-rows">
					<div class="year-row">
						<strong>Year 1</strong>
						<div class="chips">
							{#each year1Courses as code}
								<span>{code}</span>
							{/each}
						</div>
					</div>
					<div class="year-row">
						<strong>Year 2</strong>
						<div class="chips">
							<span class="selected-year2">{year12Choice}</span>
							{#each year2Courses as code}
								<span>{code}</span>
							{/each}
						</div>
					</div>
					{#if otherCourses.length}
						<div class="year-row">
							<strong>Other</strong>
							<div class="chips">
								{#each otherCourses as code}
									<span>{code}</span>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			</div>

			<textarea
				bind:value={interests}
				placeholder="e.g., I enjoy machine learning systems and software engineering for intelligent products."
				rows="6"
				disabled={loading}
			></textarea>
			<button type="submit" disabled={loading}>{loading ? 'Generating...' : 'Generate profile'}</button>
		</form>
	</section>

	<section class="results">
		{#if loading}
			<div class="loading-card">
				<div class="spinner"></div>
				<div>
					<p class="loading-title">Generating profile{loadingDots}</p>
					<p class="loading-time">Time elapsed: {elapsedSeconds.toFixed(1)}s</p>
				</div>
			</div>
		{:else if error}
			<div class="error">{error}</div>
		{:else if profile}
			<div class="stack">
				<section class="card">
					<h3>Profile overview</h3>
					<div class="stats">
						<div><span>Total credits</span><strong>{profile.total_credits}</strong></div>
						<div><span>Semester slots</span><strong>{sumSemesterSlots(profile)}</strong></div>
						<div><span>Kernel areas</span><strong>{profile.kernel_areas_selected.join(', ')}</strong></div>
						<div><span>Depth areas</span><strong>{profile.depth_areas_selected.join(', ')}</strong></div>
						<div class={profile.constraints_satisfied ? 'constraint-cell-ok' : 'constraint-cell-bad'}>
							<span>Constraints</span>
							<strong class={profile.constraints_satisfied ? 'status-ok' : 'status-bad'}>
								{profile.constraints_satisfied ? 'Met' : 'Not met'}
							</strong>
						</div>
					</div>
				</section>

				<section class="card">
					<h3>Semester plan</h3>
					<div class="grid">
						{#each terms as term}
							<div class="row">
								<div class="term">{term}</div>
								<div class="cells">
									{#each Array.from({ length: 5 }) as _, i}
										{@const row = profile.semester_plan.find((r) => r.term === term)}
										{@const code = row?.course_codes[i]}
										<button type="button" class="cell" disabled={!code} on:click={() => code && openCourseByCode(code)}>
											{#if code}
												<div class="code">{code}</div>
												<div class="name">{mapped.get(code)?.course_name || 'Name not available'}</div>
											{:else}
												<div class="empty">-</div>
											{/if}
										</button>
									{/each}
								</div>
							</div>
						{/each}
					</div>
				</section>

				<section class="card">
					<h3>Graduation requirements</h3>
					<h4>Program requirements</h4>
					<div class="program-table-wrap">
						<table class="program-table">
							<tbody>
								<tr>
									<th>Kernel/Depth</th>
									<td>
										{#if buckets}
											<table class="kernel-table">
												<tbody>
													{#each Array.from(buckets.areaRows.entries()).sort((a, b) => a[0] - b[0]) as [area, courses]}
														<tr>
															<th>Area {area}</th>
															<td class="req-courses">
																{#each courses as c}
																	<button type="button" on:click={() => openCourseByCode(c.course_code)}>{c.course_code}</button>
																{/each}
															</td>
														</tr>
													{/each}
												</tbody>
											</table>
										{/if}
									</td>
								</tr>
								<tr>
									<th>Engineering Economics</th>
									<td>{#if buckets?.engEcon[0]}<button type="button" on:click={() => openCourseByCode(buckets.engEcon[0].course_code)}>{buckets.engEcon[0].course_code}</button>{/if}</td>
								</tr>
								<tr>
									<th>Capstone</th>
									<td>{#each buckets?.capstone || [] as c}<button type="button" on:click={() => openCourseByCode(c.course_code)}>{c.course_code}</button>{/each}</td>
								</tr>
								<tr>
									<th>Science/Math</th>
									<td>{#each buckets?.sciMath || [] as c}<button type="button" on:click={() => openCourseByCode(c.course_code)}>{c.course_code}</button>{/each}</td>
								</tr>
								<tr>
									<th>Technical Electives</th>
									<td>{#each buckets?.technicalElectives || [] as c}<button type="button" on:click={() => openCourseByCode(c.course_code)}>{c.course_code}</button>{/each}</td>
								</tr>
								<tr>
									<th>HSS and CS</th>
									<td>{#each buckets?.hsscs || [] as c}<button type="button" on:click={() => openCourseByCode(c.course_code)}>{c.course_code}</button>{/each}</td>
								</tr>
								<tr>
									<th>Free Elective</th>
									<td>{#each buckets?.free || [] as c}<button type="button" on:click={() => openCourseByCode(c.course_code)}>{c.course_code}</button>{/each}</td>
								</tr>
							</tbody>
						</table>
					</div>

					<h4>CEAB requirements</h4>
					{#if profile.constraint_diagnostics?.ceab_summary?.length}
						<table class="ceab">
							<thead>
								<tr><th>Attribute</th><th>Required</th><th>Achieved</th><th>Status</th></tr>
							</thead>
							<tbody>
								{#each profile.constraint_diagnostics.ceab_summary as row}
									<tr>
										<td>{row.label}</td>
										<td>{row.required.toFixed(1)}</td>
										<td class={row.ok ? 'ceab-ok-text' : 'ceab-bad-text'}>{row.achieved.toFixed(1)}</td>
										<td class={row.ok ? 'ceab-ok-text' : 'ceab-bad-text'}>
											{row.ok ? 'OK' : row.delta.toFixed(1)}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					{/if}
				</section>

				<section class="card">
					<h3>Preference matching</h3>
					<p class="note">These courses were produced by the ranking engine based on your interests.</p>
					<div class="pref-columns">
						<div>
							<h4>Included ({profile.preferences_used.length})</h4>
							<div class="chips">{#each profile.preferences_used as p}<span class="ok-chip">{p}</span>{/each}</div>
						</div>
						<div>
							<h4>Skipped ({profile.preferences_skipped.length})</h4>
							<div class="chips">{#each profile.preferences_skipped as p}<span class="bad-chip">{p}</span>{/each}</div>
						</div>
					</div>
				</section>
			</div>
		{:else}
			<div class="empty">Enter your interests to generate a profile.</div>
		{/if}
	</section>

	<CourseDetailsModal course={selectedCourse} onClose={() => (selectedCourse = null)} />
</main>

<style>
	.page { max-width: 1180px; margin: 0 auto; padding: 22px 18px 36px; display: grid; gap: 14px; }
	.prompt-panel, .results .card, .loading-card, .error, .empty { background: white; border: 1px solid var(--border); border-radius: 12px; box-shadow: var(--shadow-sm); }
	.prompt-panel { padding: 18px; }
	h2,h3,h4 { margin: 0 0 10px; }
	p { color: var(--text-muted); margin: 0 0 10px; }
	form { display: grid; gap: 10px; }
	.choice-fieldset { border: 1px solid var(--border); border-radius: 10px; padding: 8px 10px; }
	.choice-fieldset legend { font-size: .85rem; color: var(--text-muted); padding: 0 4px; }
	.radio-row { display: flex; gap: 12px; flex-wrap: wrap; color: var(--text-muted); }
	.year12-list { background: #f8faff; border: 1px solid var(--border); border-radius: 10px; padding: 10px; }
	.year-rows { display: grid; gap: 8px; }
	.year-row { display: grid; grid-template-columns: 72px 1fr; gap: 8px; align-items: start; }
	.year-row strong { font-size: .82rem; color: var(--text-muted); padding-top: 6px; }
	textarea { width: 100%; border: 1px solid var(--border); border-radius: 10px; padding: 12px; font: inherit; resize: vertical; }
	button { border: 0; border-radius: 10px; padding: 10px 14px; background: #2563eb; color: white; cursor: pointer; }
	button:disabled { opacity: .5; cursor: not-allowed; }
	.loading-card, .error, .empty { padding: 16px; }
	.loading-card { display: flex; align-items: center; gap: 10px; }
	.loading-title { font-weight: 700; color: var(--text); margin: 0 0 4px; }
	.loading-time { margin: 0; color: var(--text-muted); font-size: .86rem; }
	.spinner { width: 24px; height: 24px; border: 3px solid #dbe4f4; border-top-color: #2563eb; border-radius: 999px; animation: spin .8s linear infinite; }
	@keyframes spin { to { transform: rotate(360deg); } }
	.stack { display: grid; gap: 12px; }
	.card { padding: 14px; }
	.stats { display:grid; grid-template-columns: repeat(auto-fit,minmax(150px,1fr)); gap: 8px; }
	.stats > div { border: 1px solid var(--border); border-radius: 8px; padding: 8px; background: #f8faff; }
	.stats span { display:block; font-size:.75rem; color: var(--text-muted); }
	.status-ok { color: #0f7a3f; }
	.status-bad { color: #b42318; }
	.constraint-cell-ok { background: #e8fbef !important; border-color: #b7ebca !important; }
	.constraint-cell-bad { background: #fdecec !important; border-color: #f9c2c2 !important; }
	.grid { border:1px solid var(--border); border-radius: 10px; overflow: hidden; }
	.row { display:grid; grid-template-columns: 58px 1fr; border-top:1px solid var(--border); }
	.row:first-child { border-top: 0; }
	.term { background:#f3f6fd; border-right:1px solid var(--border); display:grid; place-items:center; font-weight:700; }
	.cells { display:grid; grid-template-columns: repeat(5,minmax(0,1fr)); }
	.cell { border-left:1px solid var(--border); min-height:78px; padding:8px; text-align:left; border-radius:0; background:white; color: var(--text); }
	.cells .cell:first-child { border-left:0; }
	.cell:hover:enabled { background:#eef4ff; }
	.code { font-weight:700; font-size:.84rem; }
	.name { font-size:.76rem; color:var(--text-muted); margin-top:4px; }
	.program-table-wrap, .ceab { overflow: auto; border:1px solid var(--border); border-radius:10px; }
	.program-table, .ceab { width:100%; border-collapse: collapse; }
	th, td { border-bottom:1px solid var(--border); padding:10px; text-align:left; vertical-align: top; }
	.program-table > tbody > tr > th { background:#f8faff; width: 210px; font-size:.78rem; text-transform: uppercase; letter-spacing:.2px; }
	.req-courses { display:flex; gap:6px; flex-wrap: wrap; }
	.kernel-table { width: 100%; border-collapse: collapse; }
	.kernel-table th, .kernel-table td { border-bottom: 1px solid var(--border); padding: 8px; }
	.kernel-table th { width: 84px; background: #fbfcff; font-size: .78rem; color: var(--text-muted); text-transform: none; letter-spacing: 0; }
	td button { background:#eef3ff; color:#1d4ed8; border:1px solid #c8dcff; padding:6px 10px; border-radius:999px; font-size:.78rem; }
	.ceab th, .ceab td { width: auto; display: table-cell; }
	.ceab-ok-text { color:#0f7a3f; font-weight: 600; }
	.ceab-bad-text { color:#b42318; font-weight: 600; }
	.note { font-size:.84rem; }
	.pref-columns { display:grid; gap:10px; grid-template-columns:repeat(2,minmax(0,1fr)); }
	.chips { display:flex; gap:6px; flex-wrap:wrap; }
	.chips span { border-radius:999px; padding:6px 9px; font-size:.75rem; border:1px solid; }
	.selected-year2 { background:#eef3ff; color:#1d4ed8; border-color:#c8dcff; font-weight: 700; }
	.ok-chip { background:#e8fbef; color:#0f7a3f; border-color:#b7ebca; }
	.bad-chip { background:#fdecec; color:#b42318; border-color:#f9c2c2; }
	@media (max-width: 980px){ .pref-columns{ grid-template-columns:1fr; } .row{ grid-template-columns:46px 1fr; } .name{ display:none; } }
</style>

<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { supabase } from '$lib/auth';
	import { loadSession, appendEntry, clearSession } from '$lib/api/history';
	import { fetchYear12Courses, fetchConstraints, type ProgramConstraints } from '$lib/api/catalog';
	import { generateProfile, regenerateProfile } from '$lib/api/profile';
	import CourseDetailsModal from '$lib/components/CourseDetailsModal.svelte';
	import SlotEditor from '$lib/components/SlotEditor.svelte';
	import type { CourseInfo, ProfileResponse } from '$lib/types/profile';
	import {
		type FeedbackState,
		type FeedbackRecord,
		type FeedbackHonorReport,
		type HistoryEntry,
		isCapstoneCode,
		FEEDBACK_CSS_CLASS,
		HISTORY_LIMIT
	} from '$lib/types/feedback';

	const terms = ['3F', '3S', '4F', '4S'];

	// ── Prompt / generation state ─────────────────────────────────────────────
	let interests = '';
	let loading = false;
	let regenerating = false;
	let profile: ProfileResponse | null = null;
	let error: string | null = null;
	let year12Choice: 'ECE295H1' | 'ECE297H1' = 'ECE297H1';
	let year12Courses: string[] = [];
	let loadingTimer: ReturnType<typeof setInterval> | null = null;
	let elapsedSeconds = 0;
	let loadingDots = '.';

	// ── Feedback state ────────────────────────────────────────────────────────
	let currentFeedback: FeedbackRecord = {};
	let originalPreferences: string[] = [];
	let noFeedbackNotice = false;
	let honorReport: FeedbackHonorReport | null = null;
	let regenError: string | null = null;
	let iterationCounter = 0;

	// True when the current iteration-1 profile was already written to Supabase
	// by handleSubmit / handleGenerateFresh, so handleRegenerate can skip
	// re-writing that entry (avoiding a duplicate row for iter 1).
	let initialProfilePersistedToDb = false;

	// ── Iteration history ─────────────────────────────────────────────────────
	let historyEntries: HistoryEntry[] = [];
	let viewingHistoryIdx: number | null = null;

	// ── Slot editor ───────────────────────────────────────────────────────────
	let slotEditorCode: string | null = null;
	let slotEditorAnchorRect: DOMRect | null = null;

	// ── Feedback memory panel ─────────────────────────────────────────────────
	let feedbackPanelOpen = true;

	// ── Program constraints (fetched from /constraints to avoid hardcoding) ──
	let programConstraints: ProgramConstraints | null = null;

	/** Returns true if the given code is a capstone course.
	 *  Uses server-provided capstone_codes when available; falls back to the
	 *  static list in feedback.ts so the check works even before the fetch completes. */
	function checkIsCapstone(code: string): boolean {
		if (programConstraints) return programConstraints.capstone_codes.includes(code);
		return isCapstoneCode(code);
	}

	// ── Course name cache ─────────────────────────────────────────────────────
	let courseNameCache: Record<string, string> = {};

	function updateCourseNameCache(p: ProfileResponse) {
		const updates: Record<string, string> = {};
		for (const c of p.courses) updates[c.course_code] = c.course_name;
		courseNameCache = { ...courseNameCache, ...updates };
	}

	function clearAllFeedback() {
		currentFeedback = {};
		noFeedbackNotice = false;
		honorReport = null;
	}

	// ── Course detail modal ───────────────────────────────────────────────────
	let selectedCourse: CourseInfo | null = null;

	// ─────────────────────────────────────────────────────────────────────────

	onMount(async () => {
		// Server-side hooks.server.ts already guards this route.
		// Fetch program constraints (capstone codes, slot counts, etc.) from the
		// backend SSOT so the frontend never hardcodes ECE program values.
		fetchConstraints().then((c) => { if (c) programConstraints = c; });

		// Restore history from Supabase if a client is available.
		await refreshYear12Courses();
		if (supabase) {
			const saved = await loadSession(supabase);
			if (saved.entries.length > 0) {
				originalPreferences = saved.originalPreferences;
				if (saved.year12Choice === 'ECE295H1' || saved.year12Choice === 'ECE297H1') {
					year12Choice = saved.year12Choice;
				}
				const latest = saved.entries[saved.entries.length - 1];

				// If only one entry exists and it has no feedback (the initial profile
				// stored by handleSubmit/handleGenerateFresh), treat it as the current
				// profile rather than a past history entry so the dropdown doesn't
				// immediately show "Iteration 1" as history right after a first generate.
				const isSingleInitialEntry =
					saved.entries.length === 1 &&
					Object.keys(latest.feedback).length === 0;

				if (isSingleInitialEntry) {
					historyEntries = [];
					iterationCounter = latest.iteration;
				} else {
					historyEntries = saved.entries;
					iterationCounter = latest.iteration + 1;
				}

				profile = latest.profile;
				currentFeedback = { ...latest.feedback };
				if (profile) updateCourseNameCache(profile);
			}
		}
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

	// ── Initial profile generation ────────────────────────────────────────────

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		if (!interests.trim()) { error = 'Please enter your interests.'; return; }
	loading = true;
	error = null;
	profile = null;
	regenError = null;
	honorReport = null;
	noFeedbackNotice = false;
	elapsedSeconds = 0;
	loadingDots = '.';
	currentFeedback = {};
	historyEntries = [];
	viewingHistoryIdx = null;
	iterationCounter = 0;
	originalPreferences = [];
	initialProfilePersistedToDb = false;
	cycleLoadingSteps();
		try {
			profile = await generateProfile({
				interests: interests.trim(),
				num_recommendations: 15,
				year12_choice: year12Choice
			});
			iterationCounter = 1;
			originalPreferences = profile?.preferences_used
				? [...(profile.preferences_used || []), ...(profile.preferences_skipped || [])]
				: [];
			if (profile) updateCourseNameCache(profile);
			// Persist iteration 1 to Supabase: clear old history first, then write the
			// initial profile so a page refresh always restores the session correctly.
			if (supabase && profile) {
				await clearSession(supabase);
				const initEntry = { iteration: 1, profile, feedback: {}, timestamp: Date.now() };
				appendEntry(supabase, initEntry, originalPreferences, year12Choice)
					.then(() => { initialProfilePersistedToDb = true; })
					.catch((e) => {
						console.warn('[history] Could not persist initial profile — history may be lost on refresh.', e);
					});
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to generate profile. Make sure the backend is running.';
		} finally {
			loading = false;
			stopLoadingSteps();
		}
	}

	// ── Generate Fresh ────────────────────────────────────────────────────────

	async function handleGenerateFresh(event: MouseEvent) {
		event.preventDefault();
		if (!interests.trim()) { error = 'Please enter your interests.'; return; }
	loading = true;
	error = null;
	regenError = null;
	honorReport = null;
	noFeedbackNotice = false;
	profile = null;
	currentFeedback = {};
	historyEntries = [];
	viewingHistoryIdx = null;
	iterationCounter = 0;
	originalPreferences = [];
	initialProfilePersistedToDb = false;
	elapsedSeconds = 0;
	loadingDots = '.';
	cycleLoadingSteps();
	// Clear persisted history for this user before generating a fresh profile.
	if (supabase) await clearSession(supabase);
		try {
			profile = await generateProfile({
				interests: interests.trim(),
				num_recommendations: 15,
				year12_choice: year12Choice
			});
			iterationCounter = 1;
			originalPreferences = [
				...(profile?.preferences_used || []),
				...(profile?.preferences_skipped || [])
			];
			if (profile) updateCourseNameCache(profile);
			// Persist iteration 1 to Supabase so a page refresh restores it correctly.
			if (supabase && profile) {
				const initEntry = { iteration: 1, profile, feedback: {}, timestamp: Date.now() };
				appendEntry(supabase, initEntry, originalPreferences, year12Choice)
					.then(() => { initialProfilePersistedToDb = true; })
					.catch((e) => {
						console.warn('[history] Could not persist initial profile — history may be lost on refresh.', e);
					});
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to generate profile. Make sure the backend is running.';
		} finally {
			loading = false;
			stopLoadingSteps();
		}
	}

	// ── Regenerate with Feedback ──────────────────────────────────────────────

	async function handleRegenerate(event: MouseEvent) {
		event.preventDefault();
		noFeedbackNotice = false;
		regenError = null;
		honorReport = null;

		const feedbackKeys = Object.keys(currentFeedback);
		if (feedbackKeys.length === 0) { noFeedbackNotice = true; return; }

		const locked   = feedbackKeys.filter((c) => currentFeedback[c] === 'LOCK');
		const excluded = feedbackKeys.filter((c) => currentFeedback[c] === 'EXCLUDE');
		const liked    = feedbackKeys.filter((c) => currentFeedback[c] === 'LIKE');
		const disliked = feedbackKeys.filter((c) => currentFeedback[c] === 'DISLIKE');

		regenerating = true;
		elapsedSeconds = 0;
		loadingDots = '.';
		cycleLoadingSteps();
		try {
			const response = await regenerateProfile({
				year12_choice: year12Choice,
				preferences: originalPreferences,
				feedback: { locked, excluded, liked, disliked }
			});

			if (response.timed_out) {
				regenError = '⏱ The solver timed out (15 s) with these constraints. Your current profile is unchanged. Try fewer or less restrictive constraints.';
				return;
			}
			if (response.feedback_infeasible) {
				regenError = '⚠ No valid profile exists with these exact constraints. Try removing some locked or excluded courses.';
				return;
			}
			if (!response.success) {
				regenError = response.error || 'Regeneration failed.';
				return;
			}

			const submittedFeedback: FeedbackRecord = { ...currentFeedback };
			const entry: HistoryEntry = {
				iteration: iterationCounter,
				profile: profile!,
				feedback: submittedFeedback,
				timestamp: Date.now()
			};
			// Capture whether the initial profile was already written to Supabase
			// before updating historyEntries (which resets that state indirectly).
			const skipAppend = initialProfilePersistedToDb && historyEntries.length === 0;
			historyEntries = [...historyEntries, entry].slice(-HISTORY_LIMIT);
			iterationCounter += 1;
			initialProfilePersistedToDb = false;
			currentFeedback = { ...submittedFeedback };
			viewingHistoryIdx = null;
			profile = response;
			updateCourseNameCache(response);
			// Persist the history entry to Supabase, unless the initial profile was
			// already written by handleSubmit/handleGenerateFresh (avoids duplicates).
			if (supabase && !skipAppend) {
				appendEntry(supabase, entry, originalPreferences, year12Choice).catch((e) => {
					console.warn('[history] Could not persist history entry — history may be lost on refresh.', e);
				});
			}

			if (response.feedback_result) {
				honorReport = {
					liked_honored:    response.feedback_result.liked_honored ?? [],
					liked_skipped:    response.feedback_result.liked_skipped ?? [],
					disliked_honored: response.feedback_result.disliked_honored ?? [],
					disliked_forced:  response.feedback_result.disliked_forced ?? []
				};
			}
		} catch (e) {
			regenError = e instanceof Error ? e.message : 'Regeneration failed. Please try again.';
		} finally {
			regenerating = false;
			stopLoadingSteps();
		}
	}

	// ── Feedback management ───────────────────────────────────────────────────

	function setFeedback(code: string, state: FeedbackState | null) {
		if (state === null) {
			const updated = { ...currentFeedback };
			delete updated[code];
			currentFeedback = updated;
		} else {
			currentFeedback = { ...currentFeedback, [code]: state };
		}
		noFeedbackNotice = false;
		honorReport = null;
	}

	function removeFeedback(code: string) { setFeedback(code, null); }

	// ── Slot editor ───────────────────────────────────────────────────────────

	function openSlotEditor(code: string, event: MouseEvent) {
		event.stopPropagation();
		slotEditorCode = code;
		slotEditorAnchorRect = (event.currentTarget as HTMLElement).getBoundingClientRect();
	}

	function closeSlotEditor() {
		slotEditorCode = null;
		slotEditorAnchorRect = null;
	}

	function handleSlotEditorSet(code: string, state: FeedbackState | null) {
		setFeedback(code, state);
		closeSlotEditor();
	}

	// ── History navigation ────────────────────────────────────────────────────

	function viewIteration(idx: number | null) {
		viewingHistoryIdx = idx;
		closeSlotEditor();
	}

	// ── Course detail modal ───────────────────────────────────────────────────

	function openCourseByCode(code: string, p: ProfileResponse | null) {
		if (!p) return;
		selectedCourse = courseMap(p).get(code) || null;
	}

	// ── Derived values ────────────────────────────────────────────────────────

	function sumSemesterSlots(current: ProfileResponse): number {
		return current.semester_plan?.reduce((acc, row) => acc + (row.course_codes?.length || 0), 0) ?? 0;
	}

	function courseMap(current: ProfileResponse): Map<string, CourseInfo> {
		return new Map(current.courses.map((c) => [c.course_code, c]));
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
				(codes || []).map((code) => byCode.get(code)).filter((c): c is CourseInfo => Boolean(c));
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
			areaRows.set(area, courses.slice().sort((a, b) => a.course_code.localeCompare(b.course_code)));
		}

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

		const activeCapstoneCodes = programConstraints?.capstone_codes ?? ['ECE496Y1', 'APS490Y1', 'BME498Y1'];
		const engEcon = pick((c) => c.course_code === 'ECE472H1', 1);
		const capstone = pick((c) => activeCapstoneCodes.includes(c.course_code), 1);
		const sciMath = pick((c) => c.area === 7, 1);
		const technicalElectives = pick((c) => c.technical_elective && c.course_code !== 'ECE472H1', 3);
		const hsscs = pick((c) => ['hss', 'cs'].includes((c.non_technical_type || '').toLowerCase()), 4);
		const free = pick((c) => Boolean(c.free_elective), 1);

		return { areaRows, engEcon, capstone, sciMath, technicalElectives, hsscs, free, byCode };
	}

	// ── Reactive / derived ────────────────────────────────────────────────────

	$: displayProfile = viewingHistoryIdx !== null ? historyEntries[viewingHistoryIdx]?.profile ?? null : profile;
	$: isReadOnly = viewingHistoryIdx !== null;
	$: mapped = displayProfile ? courseMap(displayProfile) : new Map<string, CourseInfo>();
	$: buckets = displayProfile ? computeProgramBuckets(displayProfile) : null;
	$: year1Courses = year12Courses.filter((c) => courseLevel(c) === 1);
	$: year2Courses = year12Courses.filter((c) => courseLevel(c) === 2 && c !== 'ECE295H1' && c !== 'ECE297H1');
	$: otherCourses = year12Courses.filter((c) => {
		const lvl = courseLevel(c);
		return lvl !== 1 && lvl !== 2 && c !== 'ECE295H1' && c !== 'ECE297H1';
	});
	$: hasFeedback = Object.keys(currentFeedback).length > 0;
	$: displayFeedback = viewingHistoryIdx !== null
		? (historyEntries[viewingHistoryIdx]?.feedback ?? {})
		: currentFeedback;
	$: hasDisplayFeedback = Object.keys(displayFeedback).length > 0;
	$: feedbackByState = {
		LOCK:    Object.keys(displayFeedback).filter((c) => displayFeedback[c] === 'LOCK'),
		EXCLUDE: Object.keys(displayFeedback).filter((c) => displayFeedback[c] === 'EXCLUDE'),
		LIKE:    Object.keys(displayFeedback).filter((c) => displayFeedback[c] === 'LIKE'),
		DISLIKE: Object.keys(displayFeedback).filter((c) => displayFeedback[c] === 'DISLIKE')
	} as Record<FeedbackState, string[]>;
	$: historyDropdownItems = [
		...historyEntries.map((e, i) => ({ label: `Iteration ${e.iteration}`, idx: i })),
		{ label: `Current (Iteration ${iterationCounter})`, idx: null as number | null }
	];
</script>

<svelte:head><title>Generate Course Profile — MagellanAI</title></svelte:head>

<main class="page">
	<!-- ── Prompt panel ────────────────────────────────────────────────────── -->
	<section class="prompt-panel">
		<!-- Panel header -->
		<div class="prompt-header">
			<div>
				<div class="breadcrumb">Navigation Hub / Generate Course Profile</div>
				<h1 class="prompt-title">Generate Course Profile</h1>
				<p class="prompt-desc">
					Describe your academic interests and goals. MagellanAI will rank relevant courses,
					generate a constraint-verified profile, and chart your semester plan.
				</p>
			</div>
		</div>

		<form on:submit={handleSubmit} class="prompt-form">
			<!-- Year 2 design course selection -->
			<fieldset class="choice-fieldset">
				<legend class="choice-legend">Year 2 Design Course</legend>
				<div class="radio-row">
					<label class="radio-label">
						<input type="radio" bind:group={year12Choice} value="ECE295H1" />
						<span class="radio-code">ECE295H1</span>
					</label>
					<label class="radio-label">
						<input type="radio" bind:group={year12Choice} value="ECE297H1" />
						<span class="radio-code">ECE297H1</span>
					</label>
				</div>
			</fieldset>

			<!-- Year 1/2 course chips -->
			<div class="year12-panel">
				<div class="year12-title">
					<span class="year12-icon" aria-hidden="true">📚</span>
					Year 1 / 2 Courses — Included as CEAB Baseline
				</div>
				<div class="year-rows">
					<div class="year-row">
						<span class="year-label">Year 1</span>
						<div class="chips">
							{#each year1Courses as code}
								<span class="chip chip-neutral">{code}</span>
							{/each}
						</div>
					</div>
					<div class="year-row">
						<span class="year-label">Year 2</span>
						<div class="chips">
							<span class="chip chip-selected">{year12Choice}</span>
							{#each year2Courses as code}
								<span class="chip chip-neutral">{code}</span>
							{/each}
						</div>
					</div>
					{#if otherCourses.length}
						<div class="year-row">
							<span class="year-label">Other</span>
							<div class="chips">
								{#each otherCourses as code}
									<span class="chip chip-neutral">{code}</span>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			</div>

			<!-- Interests textarea -->
			<div class="textarea-wrap">
				<label for="interests-input" class="field-label">Your Academic Interests</label>
				<textarea
					id="interests-input"
					bind:value={interests}
					placeholder="e.g. I'm interested in machine learning systems, distributed computing, and building intelligent software products…"
					rows="5"
					disabled={loading || regenerating}
					class="interests-textarea"
				></textarea>
			</div>

			<!-- Submit button -->
			<button
				type="submit"
				class="btn-generate"
				disabled={loading || regenerating}
				aria-busy={loading}
			>
				{#if loading}
					<div class="spinner-compass sm" aria-hidden="true"></div>
					Generating profile{loadingDots}
				{:else}
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
						<circle cx="12" cy="12" r="10"/>
						<polyline points="12 6 12 12 16 14"/>
					</svg>
					Generate My Course Profile
				{/if}
			</button>
		</form>
	</section>

	<!-- ── Results area ───────────────────────────────────────────────────── -->
	<section class="results-area">
		{#if loading}
			<div class="loading-card">
				<div class="spinner-compass" aria-hidden="true"></div>
				<div class="loading-text">
					<p class="loading-title">Generating your course profile{loadingDots}</p>
					<p class="loading-subtitle">Running RAG ranking → CP-SAT solver → constraint verifier</p>
					<p class="loading-time">{elapsedSeconds.toFixed(1)}s elapsed</p>
				</div>
			</div>
		{:else if error}
			<div class="error-card">
				<span class="error-icon" aria-hidden="true">⚠</span>
				<div>
					<p class="error-title">Error</p>
					<p class="error-msg">{error}</p>
				</div>
			</div>
		{:else if displayProfile}

		<!-- ── History navigation ─────────────────────────────────────────── -->
		{#if historyEntries.length > 0}
			<div class="nav-bar">
				<div class="nav-bar-left">
					<label for="history-sel" class="nav-label">
						<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
							<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
							<path d="M3 3v5h5"/>
							<path d="M12 7v5l4 2"/>
						</svg>
						View iteration:
					</label>
					<select
						id="history-sel"
						class="history-select"
						on:change={(e) => {
							const v = (e.currentTarget as HTMLSelectElement).value;
							viewIteration(v === 'current' ? null : parseInt(v));
						}}
					>
						{#each historyEntries as entry, i}
							<option value={String(i)} selected={viewingHistoryIdx === i}>
								Iteration {entry.iteration}
							</option>
						{/each}
						<option value="current" selected={viewingHistoryIdx === null}>
							Current (Iteration {iterationCounter})
						</option>
					</select>
				</div>
				{#if isReadOnly}
					<button type="button" class="btn-back-current" on:click={() => viewIteration(null)}>
						← Back to current
					</button>
				{/if}
			</div>
		{/if}

		<!-- ── Feedback action bar ────────────────────────────────────────── -->
		{#if !isReadOnly}
			<div class="feedback-actions">
				<div class="fa-left">
					{#if hasFeedback}
						<div class="feedback-legend">
							{#if feedbackByState.LOCK.length > 0}
								<span class="leg-item fb-lock">🔒 {feedbackByState.LOCK.length}</span>
							{/if}
							{#if feedbackByState.EXCLUDE.length > 0}
								<span class="leg-item fb-exclude">❌ {feedbackByState.EXCLUDE.length}</span>
							{/if}
							{#if feedbackByState.LIKE.length > 0}
								<span class="leg-item fb-like">👍 {feedbackByState.LIKE.length}</span>
							{/if}
							{#if feedbackByState.DISLIKE.length > 0}
								<span class="leg-item fb-dislike">👎 {feedbackByState.DISLIKE.length}</span>
							{/if}
						</div>
					{/if}
				</div>
				<div class="fa-right">
					<button
						type="button"
						class="btn-fresh"
						disabled={loading || regenerating}
						on:click={handleGenerateFresh}
					>
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
							<path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/>
							<path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/>
						</svg>
						Generate Fresh
					</button>
					<button
						type="button"
						class="btn-regen"
						disabled={loading || regenerating}
						on:click={handleRegenerate}
					>
						{#if regenerating}
							<div class="spinner-compass sm" aria-hidden="true"></div>
							Regenerating{loadingDots}
						{:else}
							<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
								<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
								<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
							</svg>
							Regenerate with Feedback
						{/if}
					</button>
				</div>
			</div>

			<!-- Regeneration loading card -->
			{#if regenerating}
				<div class="loading-card loading-card-inline">
					<div class="spinner-compass sm" aria-hidden="true"></div>
					<div>
						<p class="loading-title sm">Regenerating profile with constraints{loadingDots}</p>
						<p class="loading-time">{elapsedSeconds.toFixed(1)}s elapsed</p>
					</div>
				</div>
			{/if}

			<!-- Notices -->
			{#if noFeedbackNotice}
				<div class="notice notice-info">
					ℹ No feedback has been set — profile unchanged. Use the ⚙ icon on any course slot to add feedback.
				</div>
			{/if}
			{#if regenError}
				<div class="notice notice-warn">{regenError}</div>
			{/if}

			<!-- Honor report -->
			{#if honorReport && (honorReport.liked_honored.length > 0 || honorReport.liked_skipped.length > 0 || honorReport.disliked_honored.length > 0 || honorReport.disliked_forced.length > 0)}
				<div class="honor-report">
					<div class="honor-header">
						<span class="honor-title">Feedback Report — Iteration {iterationCounter}</span>
						<button type="button" class="honor-close" on:click={() => (honorReport = null)} aria-label="Dismiss feedback report">✕</button>
					</div>
					<div class="honor-rows">
						{#each honorReport.liked_honored as code}
							<div class="honor-row honor-ok">
								<span class="honor-icon">✔</span>
								Liked <code>{code}</code> — honored (placed)
							</div>
						{/each}
						{#each honorReport.liked_skipped as code}
							<div class="honor-row honor-skip">
								<span class="honor-icon">✗</span>
								Liked <code>{code}</code> — not placed (constraint conflict)
							</div>
						{/each}
						{#each honorReport.disliked_honored as code}
							<div class="honor-row honor-ok">
								<span class="honor-icon">✔</span>
								Disliked <code>{code}</code> — successfully avoided
							</div>
						{/each}
						{#each honorReport.disliked_forced as code}
							<div class="honor-row honor-force">
								<span class="honor-icon">⚠</span>
								Disliked <code>{code}</code> — still placed (required by constraints)
							</div>
						{/each}
					</div>
				</div>
			{/if}
		{/if}

		<!-- Read-only banner -->
		{#if isReadOnly}
			<div class="readonly-banner">
				<span class="readonly-icon" aria-hidden="true">📚</span>
				Viewing Iteration {historyEntries[viewingHistoryIdx ?? 0]?.iteration} — read-only
			</div>
		{/if}

			<div class="stack">
				<!-- ── Profile overview ──────────────────────────────────────── -->
				<section class="result-card">
					<h2 class="card-title">
						<span class="card-icon" aria-hidden="true">📊</span>
						Voyage Overview
					</h2>
					<div class="stats-grid">
						<div class="stat-cell">
							<span class="stat-label">Total Credits</span>
							<strong class="stat-value">{displayProfile.total_credits}</strong>
						</div>
						<div class="stat-cell">
							<span class="stat-label">Semester Slots</span>
							<strong class="stat-value">{sumSemesterSlots(displayProfile)}</strong>
						</div>
						<div class="stat-cell">
							<span class="stat-label">Kernel Areas</span>
							<strong class="stat-value">{displayProfile.kernel_areas_selected.join(', ')}</strong>
						</div>
						<div class="stat-cell">
							<span class="stat-label">Depth Areas</span>
							<strong class="stat-value">{displayProfile.depth_areas_selected.join(', ')}</strong>
						</div>
						<div class="stat-cell {displayProfile.constraints_satisfied ? 'stat-ok' : 'stat-bad'}">
							<span class="stat-label">Constraints</span>
							<strong class="stat-value">{displayProfile.constraints_satisfied ? '✓ All Met' : '✗ Unmet'}</strong>
						</div>
						{#if displayProfile.solver_runtime_ms !== null && displayProfile.solver_runtime_ms !== undefined}
							<div class="stat-cell">
								<span class="stat-label">Solver Time</span>
								<strong class="stat-value">{(displayProfile.solver_runtime_ms / 1000).toFixed(2)}s</strong>
							</div>
						{/if}
					</div>
				</section>

				<!-- ── Semester plan grid ─────────────────────────────────────── -->
				<section class="result-card">
					<div class="grid-header">
						<h2 class="card-title">
							<span class="card-icon" aria-hidden="true">🗺</span>
							Semester Plan
						</h2>
						<div class="grid-header-right">
							{#if hasDisplayFeedback}
								<div class="feedback-legend compact">
									{#if feedbackByState.LOCK.length > 0}<span class="leg-item fb-lock">🔒 Locked</span>{/if}
									{#if feedbackByState.EXCLUDE.length > 0}<span class="leg-item fb-exclude">❌ Excluded</span>{/if}
									{#if feedbackByState.LIKE.length > 0}<span class="leg-item fb-like">👍 Liked</span>{/if}
									{#if feedbackByState.DISLIKE.length > 0}<span class="leg-item fb-dislike">👎 Disliked</span>{/if}
								</div>
							{/if}
							{#if !isReadOnly && hasFeedback}
								<button type="button" class="btn-clear-all" on:click={clearAllFeedback}>✕ Clear all</button>
							{/if}
						</div>
					</div>

					<div class="semester-grid">
						{#each terms as term}
							<div class="semester-row">
								<div class="semester-label" aria-label="Semester {term}">
									<span class="sem-term">{term}</span>
								</div>
								<div class="semester-cells">
									{#each Array.from({ length: 5 }) as _, i}
										{@const row = displayProfile.semester_plan.find((r) => r.term === term)}
										{@const code = row?.course_codes[i]}
										{@const fbState = code ? displayFeedback[code] : null}
										{@const fbClass = fbState ? FEEDBACK_CSS_CLASS[fbState] : ''}
										<div class="cell-wrap {fbClass}" class:cell-has-feedback={Boolean(fbState)}>
											<button
												type="button"
												class="course-cell"
												disabled={!code}
												on:click={() => code && openCourseByCode(code, displayProfile)}
												aria-label={code ? `View details for ${code}` : 'Empty slot'}
											>
												{#if code}
													<div class="cell-code">{code}</div>
													<div class="cell-name">{mapped.get(code)?.course_name || ''}</div>
												{:else}
													<div class="cell-empty">—</div>
												{/if}
											</button>
											{#if code && !isReadOnly}
												<button
													type="button"
													class="gear-btn"
													class:gear-active={Boolean(currentFeedback[code])}
													on:click={(e) => openSlotEditor(code, e)}
													aria-label="Set feedback for {code}"
													title="Feedback options for {code}"
												>⚙</button>
											{/if}
										</div>
									{/each}
								</div>
							</div>
						{/each}
					</div>
				</section>

				<!-- ── Feedback memory panel ──────────────────────────────────── -->
				<section class="result-card feedback-panel-card">
					<button
						type="button"
						class="panel-toggle"
						on:click={() => (feedbackPanelOpen = !feedbackPanelOpen)}
						aria-expanded={feedbackPanelOpen}
					>
						<span class="panel-toggle-label">
							<span class="card-icon" aria-hidden="true">🧭</span>
							Feedback Memory
							{#if isReadOnly}<span class="readonly-badge">read-only</span>{/if}
						</span>
						<span class="panel-chevron" class:open={feedbackPanelOpen} aria-hidden="true">▼</span>
					</button>

					{#if feedbackPanelOpen}
						<div class="panel-body">
							{#if !hasDisplayFeedback}
								<p class="panel-empty">
									{#if isReadOnly}
										No feedback was set for this iteration.
									{:else}
										No feedback applied yet. Click <span class="gear-hint" aria-hidden="true">⚙</span> on any course slot to set feedback.
									{/if}
								</p>
							{:else}
								{#if !isReadOnly && hasFeedback}
									<div class="panel-actions-row">
										<button type="button" class="btn-clear-all" on:click={clearAllFeedback}>
											✕ Clear all feedback
										</button>
									</div>
								{/if}
								{#each (['LOCK', 'EXCLUDE', 'LIKE', 'DISLIKE'] as const) as state}
									{@const entries = feedbackByState[state]}
									{#if entries.length > 0}
										<div class="panel-group">
											<div class="panel-group-label {FEEDBACK_CSS_CLASS[state]}">
												{state === 'LOCK' ? '🔒' : state === 'EXCLUDE' ? '❌' : state === 'LIKE' ? '👍' : '👎'}
												{state === 'LOCK' ? 'Locked' : state === 'EXCLUDE' ? 'Excluded' : state === 'LIKE' ? 'Liked' : 'Disliked'}
												({entries.length})
											</div>
											<div class="panel-entries">
												{#each entries as code}
													<div class="panel-entry">
														<code class="panel-code">{code}</code>
														<span class="panel-name">
															{mapped.get(code)?.course_name ?? courseNameCache[code] ?? ''}
														</span>
														{#if !isReadOnly}
															<button
																type="button"
																class="panel-remove"
																on:click={() => removeFeedback(code)}
																aria-label="Remove feedback for {code}"
															>✕</button>
														{/if}
													</div>
												{/each}
											</div>
										</div>
									{/if}
								{/each}
							{/if}
						</div>
					{/if}
				</section>

				<!-- ── Graduation requirements ────────────────────────────────── -->
				<section class="result-card">
					<h2 class="card-title">
						<span class="card-icon" aria-hidden="true">🎓</span>
						Graduation Requirements
					</h2>

					<h3 class="subsection-title">Program Requirements</h3>
					<div class="table-wrap">
						<table class="req-table">
							<tbody>
								<tr>
									<th>Kernel / Depth</th>
									<td>
										{#if buckets}
											<table class="kernel-inner-table">
												<tbody>
													{#each Array.from(buckets.areaRows.entries()).sort((a, b) => a[0] - b[0]) as [area, courses]}
														<tr>
															<th>Area {area}</th>
															<td class="req-courses">
																{#each courses as c}
																	<button
																		type="button"
																		class="course-chip-btn"
																		on:click={() => openCourseByCode(c.course_code, displayProfile)}
																	>{c.course_code}</button>
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
									<td>
										{#if buckets?.engEcon[0]}
											<button type="button" class="course-chip-btn" on:click={() => openCourseByCode(buckets!.engEcon[0].course_code, displayProfile)}>
												{buckets?.engEcon[0].course_code}
											</button>
										{/if}
									</td>
								</tr>
								<tr>
									<th>Capstone</th>
									<td class="req-courses">
										{#each buckets?.capstone || [] as c}
											<button type="button" class="course-chip-btn capstone-chip" on:click={() => openCourseByCode(c.course_code, displayProfile)}>
												{c.course_code}
											</button>
										{/each}
									</td>
								</tr>
								<tr>
									<th>Science / Math</th>
									<td class="req-courses">
										{#each buckets?.sciMath || [] as c}
											<button type="button" class="course-chip-btn" on:click={() => openCourseByCode(c.course_code, displayProfile)}>{c.course_code}</button>
										{/each}
									</td>
								</tr>
								<tr>
									<th>Technical Electives</th>
									<td class="req-courses">
										{#each buckets?.technicalElectives || [] as c}
											<button type="button" class="course-chip-btn" on:click={() => openCourseByCode(c.course_code, displayProfile)}>{c.course_code}</button>
										{/each}
									</td>
								</tr>
								<tr>
									<th>HSS &amp; CS</th>
									<td class="req-courses">
										{#each buckets?.hsscs || [] as c}
											<button type="button" class="course-chip-btn" on:click={() => openCourseByCode(c.course_code, displayProfile)}>{c.course_code}</button>
										{/each}
									</td>
								</tr>
								<tr>
									<th>Free Elective</th>
									<td class="req-courses">
										{#each buckets?.free || [] as c}
											<button type="button" class="course-chip-btn" on:click={() => openCourseByCode(c.course_code, displayProfile)}>{c.course_code}</button>
										{/each}
									</td>
								</tr>
							</tbody>
						</table>
					</div>

					<h3 class="subsection-title">CEAB Academic Units</h3>
					{#if displayProfile.constraint_diagnostics?.ceab_summary?.length}
						<div class="table-wrap">
							<table class="ceab-table">
								<thead>
									<tr>
										<th>Attribute</th>
										<th>Required</th>
										<th>Achieved</th>
										<th>Status</th>
									</tr>
								</thead>
								<tbody>
									{#each displayProfile.constraint_diagnostics.ceab_summary as row}
										<tr>
											<td class="ceab-label">{row.label}</td>
											<td>{row.required.toFixed(1)}</td>
											<td class={row.ok ? 'ceab-ok' : 'ceab-bad'}>{row.achieved.toFixed(1)}</td>
											<td class={row.ok ? 'ceab-ok' : 'ceab-bad'}>
												{row.ok ? '✓' : `−${Math.abs(row.delta).toFixed(1)}`}
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{/if}
				</section>

				<!-- ── Preference matching ────────────────────────────────────── -->
				<section class="result-card">
					<h2 class="card-title">
						<span class="card-icon" aria-hidden="true">⭐</span>
						Preference Matching
					</h2>
					<p class="pref-note">Courses ranked by the RAG engine from your interests description.</p>
					<div class="pref-columns">
						<div class="pref-col">
							<h3 class="pref-col-title">
								<span class="pref-dot pref-dot-ok" aria-hidden="true"></span>
								Included ({displayProfile.preferences_used.length})
							</h3>
							<div class="chips">
								{#each displayProfile.preferences_used as p}
									<span class="chip chip-ok">{p}</span>
								{/each}
							</div>
						</div>
						<div class="pref-col">
							<h3 class="pref-col-title">
								<span class="pref-dot pref-dot-skip" aria-hidden="true"></span>
								Skipped ({displayProfile.preferences_skipped.length})
							</h3>
							<div class="chips">
								{#each displayProfile.preferences_skipped as p}
									<span class="chip chip-skip">{p}</span>
								{/each}
							</div>
						</div>
					</div>
				</section>
			</div>
		{:else}
			<div class="empty-state">
				<span class="empty-icon" aria-hidden="true">🧭</span>
				<p class="empty-text">Enter your interests and click <em>Generate My Course Profile</em> to chart your voyage.</p>
			</div>
		{/if}
	</section>
</main>

<!-- Course detail modal -->
<CourseDetailsModal course={selectedCourse} onClose={() => (selectedCourse = null)} />

<!-- Slot editor floating popup -->
{#if slotEditorCode && !isReadOnly}
	<SlotEditor
		course={mapped.get(slotEditorCode) ?? null}
		currentState={currentFeedback[slotEditorCode] ?? null}
		isCapstone={checkIsCapstone(slotEditorCode)}
		anchorRect={slotEditorAnchorRect}
		onSet={(state) => handleSlotEditorSet(slotEditorCode!, state)}
		onClose={closeSlotEditor}
	/>
{/if}

<style>
	/* ── Page layout ─────────────────────────────────────────────────────────── */
	.page {
		max-width: 1200px;
		margin: 0 auto;
		padding: 24px 20px 48px;
		display: grid;
		gap: 18px;
	}

	/* ── Prompt panel ─────────────────────────────────────────────────────────── */
	.prompt-panel {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 22px 22px 18px;
		box-shadow: var(--shadow-sm);
		animation: fade-in 0.4s ease;
	}

	.prompt-header { margin-bottom: 18px; }

	.breadcrumb {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.63rem;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--text-faint);
		margin-bottom: 8px;
	}

	.prompt-title {
		font-family: 'Cinzel', serif;
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--gold);
		letter-spacing: 0.06em;
		margin: 0 0 6px;
	}

	.prompt-desc {
		font-size: 0.86rem;
		color: var(--text-muted);
		margin: 0;
		line-height: 1.6;
	}

	.prompt-form { display: grid; gap: 14px; }

	/* ── Year 2 choice ────────────────────────────────────────────────────────── */
	.choice-fieldset {
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 12px 14px 10px;
	}
	.choice-legend {
		font-size: 0.79rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-muted);
		padding: 0 4px;
	}
	.radio-row {
		display: flex;
		gap: 18px;
		flex-wrap: wrap;
		margin-top: 8px;
	}
	.radio-label {
		display: flex;
		align-items: center;
		gap: 8px;
		cursor: pointer;
		font-size: 0.88rem;
		color: var(--text-muted);
	}
	.radio-label:hover { color: var(--text); }
	.radio-code {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.84rem;
	}
	input[type='radio'] { accent-color: var(--ocean-light); cursor: pointer; }

	/* ── Year 1/2 courses panel ───────────────────────────────────────────────── */
	.year12-panel {
		background: var(--surface-soft);
		border: 1px solid var(--border-soft);
		border-radius: var(--radius-sm);
		padding: 12px 14px;
	}
	.year12-title {
		font-size: 0.79rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-muted);
		margin-bottom: 10px;
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.year12-icon { font-size: 0.9rem; }
	.year-rows { display: grid; gap: 8px; }
	.year-row { display: grid; grid-template-columns: 62px 1fr; gap: 8px; align-items: start; }
	.year-label {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.7rem;
		color: var(--text-faint);
		font-weight: 600;
		padding-top: 5px;
	}
	.chips { display: flex; flex-wrap: wrap; gap: 5px; }
	.chip {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.7rem;
		border-radius: 999px;
		padding: 3px 8px;
		border: 1px solid;
	}
	.chip-neutral {
		background: var(--surface-raised);
		border-color: var(--border);
		color: var(--text-muted);
	}
	.chip-selected {
		background: rgba(32, 119, 178, 0.15);
		border-color: var(--ocean);
		color: var(--ocean-bright);
		font-weight: 700;
	}
	.chip-ok {
		background: var(--success-bg);
		border-color: var(--success-border);
		color: var(--success-text);
	}
	.chip-skip {
		background: var(--danger-bg);
		border-color: var(--danger-border);
		color: var(--danger-text);
	}

	/* ── Textarea ─────────────────────────────────────────────────────────────── */
	.textarea-wrap { display: grid; gap: 6px; }
	.field-label {
		font-size: 0.74rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-muted);
	}
	.interests-textarea {
		width: 100%;
		background: var(--surface-raised);
		color: var(--text);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 12px 14px;
		font-family: 'Raleway', sans-serif;
		font-size: 0.9rem;
		line-height: 1.6;
		resize: vertical;
		transition: border-color 0.18s, box-shadow 0.18s;
	}
	.interests-textarea:focus {
		outline: none;
		border-color: var(--ocean-light);
		box-shadow: 0 0 0 3px rgba(32, 119, 178, 0.18);
	}
	.interests-textarea::placeholder { color: var(--text-faint); }
	.interests-textarea:disabled { opacity: 0.6; cursor: not-allowed; }

	/* ── Generate button ──────────────────────────────────────────────────────── */
	.btn-generate {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 10px;
		padding: 13px 20px;
		border-radius: var(--radius-sm);
		border: 1px solid var(--ocean);
		background: linear-gradient(135deg, var(--ocean) 0%, var(--ocean-dim) 100%);
		color: var(--text);
		font-family: 'Raleway', sans-serif;
		font-size: 0.92rem;
		font-weight: 700;
		letter-spacing: 0.04em;
		cursor: pointer;
		transition: all 0.2s ease;
		box-shadow: 0 4px 18px rgba(32, 119, 178, 0.28);
	}
	.btn-generate:hover:not(:disabled) {
		transform: translateY(-2px);
		box-shadow: 0 6px 24px rgba(32, 119, 178, 0.42);
		filter: brightness(1.1);
	}
	.btn-generate:disabled {
		opacity: 0.55;
		cursor: not-allowed;
		transform: none;
	}

	/* ── Results area ─────────────────────────────────────────────────────────── */
	.results-area { display: grid; gap: 12px; }

	/* ── Loading cards ────────────────────────────────────────────────────────── */
	.loading-card {
		display: flex;
		align-items: center;
		gap: 16px;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 22px 22px;
		box-shadow: var(--shadow-sm);
		animation: fade-in 0.3s ease;
	}
	.loading-card-inline {
		background: var(--info-bg);
		border-color: var(--info-border);
		padding: 12px 16px;
		border-radius: var(--radius-sm);
	}
	.loading-text { display: grid; gap: 2px; }
	.loading-title {
		font-weight: 700;
		color: var(--text);
		margin: 0;
		font-size: 0.96rem;
	}
	.loading-title.sm { font-size: 0.9rem; color: var(--info-text); }
	.loading-subtitle { font-size: 0.84rem; color: var(--text-muted); margin: 0; }
	.loading-time { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: var(--text-faint); margin: 0; }

	/* ── Error card ───────────────────────────────────────────────────────────── */
	.error-card {
		display: flex;
		align-items: flex-start;
		gap: 14px;
		background: var(--danger-bg);
		border: 1px solid var(--danger-border);
		border-radius: var(--radius);
		padding: 18px 20px;
	}
	.error-icon { font-size: 1.4rem; line-height: 1; flex-shrink: 0; }
	.error-title { font-weight: 700; color: var(--danger-text); margin: 0 0 4px; font-size: 0.9rem; }
	.error-msg { color: var(--danger-text); margin: 0; font-size: 0.85rem; opacity: 0.85; }

	/* ── History nav bar ──────────────────────────────────────────────────────── */
	.nav-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		flex-wrap: wrap;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 10px 14px;
		box-shadow: var(--shadow-sm);
	}
	.nav-bar-left { display: flex; align-items: center; gap: 8px; }
	.nav-label {
		display: flex;
		align-items: center;
		gap: 5px;
		font-size: 0.82rem;
		color: var(--text-muted);
		font-weight: 500;
		white-space: nowrap;
		cursor: default;
	}
	.history-select {
		background: var(--surface-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		color: var(--text);
		font-size: 0.8rem;
		padding: 5px 8px;
		cursor: pointer;
		font-family: 'Raleway', sans-serif;
	}
	.btn-back-current {
		padding: 6px 12px;
		border-radius: var(--radius-sm);
		border: 1px solid var(--ocean);
		background: rgba(32, 119, 178, 0.12);
		color: var(--ocean-bright);
		font-size: 0.78rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.18s ease;
		white-space: nowrap;
	}
	.btn-back-current:hover { background: rgba(32, 119, 178, 0.22); }

	/* ── Feedback action bar ──────────────────────────────────────────────────── */
	.feedback-actions {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		flex-wrap: wrap;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 10px 14px;
		box-shadow: var(--shadow-sm);
	}
	.fa-left { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
	.fa-right { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

	.feedback-legend {
		display: flex;
		gap: 5px;
		flex-wrap: wrap;
		align-items: center;
	}
	.feedback-legend.compact .leg-item { font-size: 0.73rem; padding: 2px 7px; }

	.leg-item {
		border-radius: 999px;
		padding: 3px 9px;
		font-size: 0.76rem;
		font-weight: 600;
		border: 1.5px solid;
	}
	.leg-item.fb-lock    { background: var(--fb-lock-bg);    border-color: var(--fb-lock-border);    color: var(--fb-lock-text); }
	.leg-item.fb-exclude { background: var(--fb-exclude-bg); border-color: var(--fb-exclude-border); color: var(--fb-exclude-text); }
	.leg-item.fb-like    { background: var(--fb-like-bg);    border-color: var(--fb-like-border);    color: var(--fb-like-text); }
	.leg-item.fb-dislike { background: var(--fb-dislike-bg); border-color: var(--fb-dislike-border); color: var(--fb-dislike-text); }

	.btn-fresh {
		display: flex;
		align-items: center;
		gap: 7px;
		padding: 7px 13px;
		border-radius: var(--radius-sm);
		border: 1px solid var(--border);
		background: var(--surface-raised);
		color: var(--text-muted);
		font-size: 0.8rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.18s ease;
	}
	.btn-fresh:hover:not(:disabled) {
		border-color: var(--gold-dim);
		color: var(--gold);
		background: rgba(201, 168, 76, 0.07);
	}
	.btn-fresh:disabled { opacity: 0.5; cursor: not-allowed; }

	.btn-regen {
		display: flex;
		align-items: center;
		gap: 7px;
		padding: 7px 14px;
		border-radius: var(--radius-sm);
		border: 1px solid var(--ocean);
		background: rgba(32, 119, 178, 0.15);
		color: var(--ocean-bright);
		font-size: 0.8rem;
		font-weight: 700;
		cursor: pointer;
		transition: all 0.18s ease;
	}
	.btn-regen:hover:not(:disabled) {
		background: rgba(32, 119, 178, 0.25);
		box-shadow: var(--glow-ocean);
		transform: translateY(-1px);
	}
	.btn-regen:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

	/* ── Notice banners ───────────────────────────────────────────────────────── */
	.notice {
		border-radius: var(--radius-sm);
		padding: 10px 14px;
		font-size: 0.84rem;
		border: 1px solid;
		line-height: 1.5;
	}
	.notice-info { background: var(--info-bg); border-color: var(--info-border); color: var(--info-text); }
	.notice-warn { background: var(--warn-bg); border-color: var(--warn-border); color: var(--warn-text); }

	/* ── Honor report ─────────────────────────────────────────────────────────── */
	.honor-report {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 12px 16px;
		box-shadow: var(--shadow-sm);
	}
	.honor-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 10px;
	}
	.honor-title {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.68rem;
		font-weight: 600;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-muted);
	}
	.honor-close {
		background: none;
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text-faint);
		font-size: 0.7rem;
		padding: 2px 6px;
		cursor: pointer;
		transition: all 0.12s;
	}
	.honor-close:hover { background: var(--danger-bg); color: var(--danger-text); }

	.honor-rows { display: grid; gap: 4px; }
	.honor-row {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 0.82rem;
		padding: 3px 0;
	}
	.honor-icon { font-size: 0.88rem; flex-shrink: 0; }
	.honor-ok    { color: var(--success-text); }
	.honor-skip  { color: var(--danger-text); }
	.honor-force { color: var(--warn-text); }
	.honor-row code {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.8rem;
		background: var(--surface-raised);
		border: 1px solid var(--border);
		border-radius: 3px;
		padding: 1px 5px;
	}

	/* ── Read-only banner ─────────────────────────────────────────────────────── */
	.readonly-banner {
		display: flex;
		align-items: center;
		gap: 8px;
		background: var(--info-bg);
		border: 1px solid var(--info-border);
		border-radius: var(--radius-sm);
		padding: 10px 14px;
		font-size: 0.84rem;
		color: var(--info-text);
	}
	.readonly-icon { font-size: 1rem; }

	/* ── Result cards ─────────────────────────────────────────────────────────── */
	.stack { display: grid; gap: 12px; }
	.result-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		box-shadow: var(--shadow-sm);
		padding: 18px 20px;
		animation: fade-in 0.4s ease;
	}

	.card-title {
		font-family: 'Cinzel', serif;
		font-size: 1.0rem;
		font-weight: 600;
		letter-spacing: 0.05em;
		color: var(--text);
		margin: 0 0 16px;
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.card-icon { font-size: 1rem; }

	/* ── Profile overview stats ───────────────────────────────────────────────── */
	.stats-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
		gap: 8px;
	}
	.stat-cell {
		background: var(--surface-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 10px 12px;
	}
	.stat-label {
		display: block;
		font-size: 0.7rem;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-muted);
		margin-bottom: 4px;
	}
	.stat-value {
		font-family: 'JetBrains Mono', monospace;
		font-size: 1.0rem;
		font-weight: 700;
		color: var(--text);
		display: block;
	}
	.stat-ok { border-color: var(--success-border); background: var(--success-bg); }
	.stat-ok .stat-value { color: var(--success-text); }
	.stat-bad { border-color: var(--danger-border); background: var(--danger-bg); }
	.stat-bad .stat-value { color: var(--danger-text); }

	/* ── Grid header ──────────────────────────────────────────────────────────── */
	.grid-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 8px;
		flex-wrap: wrap;
		margin-bottom: 14px;
	}
	.grid-header .card-title { margin: 0; }
	.grid-header-right {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-wrap: wrap;
	}

	/* ── Semester grid ────────────────────────────────────────────────────────── */
	.semester-grid {
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		overflow: hidden;
	}

	.semester-row {
		display: grid;
		grid-template-columns: 56px 1fr;
		border-top: 1px solid var(--border);
	}
	.semester-row:first-child { border-top: none; }

	.semester-label {
		background: var(--surface-raised);
		border-right: 1px solid var(--border);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 6px;
	}
	.sem-term {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.84rem;
		font-weight: 700;
		color: var(--text-muted);
		letter-spacing: 0.06em;
	}

	.semester-cells {
		display: grid;
		grid-template-columns: repeat(5, minmax(0, 1fr));
	}

	/* ── Course cell wrapper ──────────────────────────────────────────────────── */
	.cell-wrap {
		position: relative;
		border-left: 1px solid var(--border);
		background: var(--surface);
		transition: background 0.15s ease;
	}
	.semester-cells .cell-wrap:first-child { border-left: none; }

	/* Feedback tints */
	.cell-wrap.fb-lock    { background: var(--fb-lock-bg); }
	.cell-wrap.fb-exclude { background: var(--fb-exclude-bg); }
	.cell-wrap.fb-like    { background: var(--fb-like-bg); }
	.cell-wrap.fb-dislike { background: var(--fb-dislike-bg); }

	/* Left accent stripe */
	.cell-wrap.fb-lock::before    { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--fb-lock-accent); box-shadow: 2px 0 8px rgba(0,255,133,0.25); }
	.cell-wrap.fb-exclude::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--fb-exclude-accent); box-shadow: 2px 0 8px rgba(255,111,97,0.25); }
	.cell-wrap.fb-like::before    { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--fb-like-accent); box-shadow: 2px 0 8px rgba(215,218,220,0.20); }
	.cell-wrap.fb-dislike::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--fb-dislike-accent); box-shadow: 2px 0 8px rgba(218,165,32,0.30); }

	/* ── Course cell ─────────────────────────────────────────────────────────── */
	.course-cell {
		width: 100%;
		min-height: 80px;
		padding: 9px 8px 6px;
		text-align: left;
		border: none;
		border-radius: 0;
		background: transparent;
		color: var(--text);
		cursor: pointer;
		transition: background 0.12s ease;
	}
	.course-cell:disabled { cursor: default; }
	.course-cell:hover:not(:disabled) { background: rgba(74, 174, 232, 0.06); }

	.cell-code {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.84rem;
		font-weight: 700;
		color: var(--ocean-bright);
		line-height: 1.2;
	}
	.cell-name {
		font-size: 0.76rem;
		color: var(--text-muted);
		margin-top: 3px;
		line-height: 1.3;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	.cell-empty {
		color: var(--text-faint);
		font-size: 0.8rem;
		padding-top: 28px;
		text-align: center;
	}

	/* ── Gear button ─────────────────────────────────────────────────────────── */
	.gear-btn {
		position: absolute;
		top: 4px;
		right: 4px;
		width: 30px;
		height: 30px;
		border: 1px solid transparent;
		border-radius: 5px;
		background: transparent;
		color: var(--text-faint);
		font-size: 1rem;
		padding: 0;
		display: grid;
		place-items: center;
		cursor: pointer;
		opacity: 0;
		transition: opacity 0.15s ease, background 0.12s ease, border-color 0.12s ease, color 0.12s ease;
		line-height: 1;
	}
	.cell-wrap:hover .gear-btn { opacity: 1; }
	.gear-btn:hover {
		background: var(--surface-hover);
		border-color: var(--ocean-dim);
		color: var(--ocean-light);
	}
	.gear-btn.gear-active { opacity: 1; color: var(--gold); }

	/* ── Clear all button ────────────────────────────────────────────────────── */
	.btn-clear-all {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 4px 10px;
		border-radius: var(--radius-sm);
		border: 1px solid var(--compass-red);
		background: rgba(192, 57, 43, 0.08);
		color: var(--compass-red);
		font-size: 0.72rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.15s ease;
		white-space: nowrap;
	}
	.btn-clear-all:hover { background: rgba(192, 57, 43, 0.18); }

	/* ── Feedback memory panel ───────────────────────────────────────────────── */
	.feedback-panel-card { padding: 0; }

	.panel-toggle {
		width: 100%;
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 14px 20px;
		background: none;
		border: none;
		color: var(--text);
		font-size: 0.9rem;
		cursor: pointer;
		border-radius: var(--radius);
		text-align: left;
		transition: background 0.15s ease;
	}
	.panel-toggle:hover { background: var(--surface-hover); }

	.panel-toggle-label {
		display: flex;
		align-items: center;
		gap: 8px;
		font-family: 'Cinzel', serif;
		font-size: 0.95rem;
		font-weight: 600;
		letter-spacing: 0.04em;
	}

	.readonly-badge {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.62rem;
		font-weight: 600;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		padding: 2px 7px;
		border-radius: 999px;
		background: var(--info-bg);
		border: 1px solid var(--info-border);
		color: var(--info-text);
		margin-left: 4px;
	}

	.panel-chevron {
		font-size: 0.68rem;
		color: var(--text-faint);
		transition: transform 0.18s ease;
	}
	.panel-chevron.open { transform: rotate(180deg); }

	.panel-body { padding: 0 20px 16px; }
	.panel-empty { font-size: 0.84rem; color: var(--text-muted); margin: 0; }
	.gear-hint { font-size: 1rem; }

	.panel-actions-row {
		display: flex;
		justify-content: flex-end;
		margin-bottom: 12px;
	}

	.panel-group { margin-bottom: 12px; }
	.panel-group:last-child { margin-bottom: 0; }

	.panel-group-label {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		font-size: 0.76rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		margin-bottom: 8px;
		padding: 3px 9px;
		border-radius: 999px;
		border: 1.5px solid;
	}
	.panel-group-label.fb-lock    { background: var(--fb-lock-bg);    border-color: var(--fb-lock-border);    color: var(--fb-lock-text); }
	.panel-group-label.fb-exclude { background: var(--fb-exclude-bg); border-color: var(--fb-exclude-border); color: var(--fb-exclude-text); }
	.panel-group-label.fb-like    { background: var(--fb-like-bg);    border-color: var(--fb-like-border);    color: var(--fb-like-text); }
	.panel-group-label.fb-dislike { background: var(--fb-dislike-bg); border-color: var(--fb-dislike-border); color: var(--fb-dislike-text); }

	.panel-entries { display: flex; flex-direction: column; gap: 4px; }
	.panel-entry {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 6px 10px;
		background: var(--surface-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
	}
	.panel-code {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.84rem;
		font-weight: 700;
		color: var(--ocean-bright);
		flex-shrink: 0;
		background: none;
		border: none;
		padding: 0;
	}
	.panel-name {
		font-size: 0.82rem;
		color: var(--text-muted);
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.panel-remove {
		flex-shrink: 0;
		background: none;
		border: 1px solid var(--border);
		border-radius: 4px;
		padding: 2px 6px;
		font-size: 0.66rem;
		color: var(--text-faint);
		cursor: pointer;
		transition: all 0.12s ease;
	}
	.panel-remove:hover { background: var(--danger-bg); border-color: var(--danger-border); color: var(--danger-text); }

	/* ── Requirements tables ──────────────────────────────────────────────────── */
	.subsection-title {
		font-family: 'Cinzel', serif;
		font-size: 0.82rem;
		font-weight: 600;
		letter-spacing: 0.06em;
		color: var(--text-muted);
		text-transform: uppercase;
		margin: 16px 0 10px;
	}
	.result-card > .subsection-title:first-of-type { margin-top: 0; }

	.table-wrap {
		overflow-x: auto;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		margin-bottom: 4px;
	}

	.req-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.9rem;
	}
	.req-table th,
	.req-table td {
		border-bottom: 1px solid var(--border);
		padding: 10px 14px;
		text-align: left;
		vertical-align: top;
	}
	.req-table tbody tr:last-child th,
	.req-table tbody tr:last-child td { border-bottom: none; }
	.req-table > tbody > tr > th {
		background: var(--surface-raised);
		width: 180px;
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.77rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--gold);
		white-space: nowrap;
	}

	.kernel-inner-table { width: 100%; border-collapse: collapse; }
	.kernel-inner-table th,
	.kernel-inner-table td {
		border-bottom: 1px solid var(--border-soft);
		padding: 6px 10px;
		text-align: left;
	}
	.kernel-inner-table tbody tr:last-child th,
	.kernel-inner-table tbody tr:last-child td { border-bottom: none; }
	.kernel-inner-table th {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.77rem;
		color: var(--text-muted);
		font-weight: 500;
		width: 72px;
		background: transparent;
	}

	.req-courses {
		display: flex;
		gap: 5px;
		flex-wrap: wrap;
		align-items: center;
		padding: 4px 0;
	}

	.course-chip-btn {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.76rem;
		font-weight: 600;
		padding: 4px 10px;
		border-radius: 999px;
		border: 1px solid var(--ocean-dim);
		background: rgba(32, 119, 178, 0.1);
		color: var(--ocean-bright);
		cursor: pointer;
		transition: all 0.15s ease;
	}
	.course-chip-btn:hover {
		background: rgba(32, 119, 178, 0.22);
		border-color: var(--ocean-light);
		transform: translateY(-1px);
	}
	.capstone-chip {
		border-color: var(--gold-dim);
		background: rgba(201, 168, 76, 0.1);
		color: var(--gold);
	}
	.capstone-chip:hover { background: rgba(201, 168, 76, 0.2); border-color: var(--gold); }

	/* CEAB table */
	.ceab-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.9rem;
	}
	.ceab-table th {
		background: var(--surface-raised);
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.73rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-muted);
		font-weight: 500;
		padding: 9px 12px;
		border-bottom: 1px solid var(--border);
		text-align: left;
	}
	.ceab-table td {
		padding: 8px 12px;
		border-bottom: 1px solid var(--border-soft);
	}
	.ceab-table tbody tr:last-child td { border-bottom: none; }
	.ceab-label { font-weight: 500; }
	.ceab-ok { color: var(--success-text); font-weight: 700; }
	.ceab-bad { color: var(--danger-text); font-weight: 700; }

	/* ── Preference matching ──────────────────────────────────────────────────── */
	.pref-note {
		font-size: 0.82rem;
		color: var(--text-muted);
		margin: 0 0 14px;
	}
	.pref-columns {
		display: grid;
		gap: 14px;
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
	.pref-col-title {
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--text-muted);
		margin: 0 0 8px;
		display: flex;
		align-items: center;
		gap: 7px;
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	.pref-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.pref-dot-ok   { background: var(--success-text); }
	.pref-dot-skip { background: var(--danger-text); }

	/* ── Empty state ─────────────────────────────────────────────────────────── */
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 14px;
		padding: 60px 20px;
		text-align: center;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		box-shadow: var(--shadow-sm);
	}
	.empty-icon { font-size: 2.5rem; opacity: 0.3; }
	.empty-text { color: var(--text-muted); font-size: 0.9rem; max-width: 360px; margin: 0; line-height: 1.6; }

	/* ── Responsive ──────────────────────────────────────────────────────────── */
	@media (max-width: 980px) {
		.pref-columns { grid-template-columns: 1fr; }
		.semester-row { grid-template-columns: 42px 1fr; }
		.cell-name { display: none; }
		.fa-right { width: 100%; justify-content: flex-end; }
		.nav-bar { flex-direction: column; align-items: flex-start; }
		.grid-header-right { width: 100%; justify-content: flex-start; }
	}

	@media (max-width: 600px) {
		.page { padding: 16px 14px 36px; }
		.prompt-panel { padding: 16px 16px 14px; }
		.stats-grid { grid-template-columns: repeat(2, 1fr); }
	}
</style>

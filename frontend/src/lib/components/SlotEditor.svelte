<script lang="ts">
	import type { CourseInfo } from '$lib/types/profile';
	import type { FeedbackState } from '$lib/types/feedback';

	let {
		course,
		currentState,
		isCapstone = false,
		anchorRect,
		onSet,
		onClose
	}: {
		course: CourseInfo | null;
		currentState: FeedbackState | null;
		isCapstone?: boolean;
		anchorRect: DOMRect | null;
		onSet: (state: FeedbackState | null) => void;
		onClose: () => void;
	} = $props();

	const POPUP_W = 272;
	const POPUP_H_MAX = 280;

	function popupStyle(rect: DOMRect | null): string {
		if (!rect) return 'display:none';
		let top  = rect.bottom + 8;
		let left = rect.left;
		if (typeof window !== 'undefined') {
			if (left + POPUP_W > window.innerWidth - 8)
				left = Math.max(8, window.innerWidth - POPUP_W - 8);
			if (top + POPUP_H_MAX > window.innerHeight - 8)
				top = Math.max(8, rect.top - POPUP_H_MAX - 8);
		}
		return `top:${top}px;left:${left}px;width:${POPUP_W}px`;
	}

	function toggle(state: FeedbackState) {
		onSet(currentState === state ? null : state);
	}

	function handleOverlay(e: MouseEvent) {
		if (e.target === e.currentTarget) onClose();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') onClose();
	}

	const feedbackOptions: Array<{
		state: FeedbackState;
		icon: string;
		label: string;
		desc: string;
	}> = [
		{ state: 'LOCK',    icon: '🔒', label: 'Lock',    desc: 'Must appear in regenerated profile' },
		{ state: 'EXCLUDE', icon: '❌', label: 'Exclude',  desc: 'Must not appear in regenerated profile' },
		{ state: 'LIKE',    icon: '👍', label: 'Like',    desc: 'Strongly preferred (soft boost)' },
		{ state: 'DISLIKE', icon: '👎', label: 'Dislike', desc: 'Discouraged (soft penalty)' },
	];
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- Transparent overlay to catch outside clicks -->
<div class="se-overlay" role="presentation" onclick={handleOverlay}></div>

<!-- Floating popup -->
<div
	class="se-popup"
	style={popupStyle(anchorRect)}
	role="dialog"
	aria-modal="true"
	aria-label="Slot feedback editor for {course?.course_code}"
>
	<!-- Header -->
	<div class="se-header">
		<div class="se-course-info">
			<span class="se-code">{course?.course_code ?? ''}</span>
			<span class="se-name">{course?.course_name ?? ''}</span>
		</div>
		<button
			type="button"
			class="se-close"
			onclick={onClose}
			aria-label="Close feedback editor"
		>
			<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
				<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
			</svg>
		</button>
	</div>

	<!-- Capstone notice -->
	{#if isCapstone}
		<div class="se-capstone-notice">
			<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
				<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
			</svg>
			Applies to both capstone slots (4F and 4S)
		</div>
	{/if}

	<!-- Divider -->
	<div class="se-divider" aria-hidden="true"></div>

	<!-- Feedback options -->
	<div class="se-options">
		{#each feedbackOptions as opt}
			<button
				type="button"
				class="se-btn se-{opt.state.toLowerCase()}"
				class:se-active={currentState === opt.state}
				onclick={() => toggle(opt.state)}
				title={opt.desc}
				aria-pressed={currentState === opt.state}
			>
				<span class="se-btn-icon" aria-hidden="true">{opt.icon}</span>
				<span class="se-btn-label">{opt.label}</span>
			</button>
		{/each}
	</div>

	{#if currentState}
		<button
			type="button"
			class="se-clear"
			onclick={() => onSet(null)}
		>
			<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
				<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
			</svg>
			Clear feedback
		</button>
	{/if}
</div>

<style>
	.se-overlay {
		position: fixed;
		inset: 0;
		z-index: 199;
		cursor: default;
	}

	.se-popup {
		position: fixed;
		z-index: 200;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		box-shadow: var(--shadow-lg), var(--glow-ocean);
		padding: 14px;
		animation: se-slide-in 0.14s ease;
	}

	/* Subtle top accent */
	.se-popup::before {
		content: '';
		position: absolute;
		top: 0; left: 0; right: 0;
		height: 2px;
		border-radius: var(--radius) var(--radius) 0 0;
		background: linear-gradient(90deg, var(--gold-dim), var(--ocean));
		opacity: 0.5;
	}

	@keyframes se-slide-in {
		from { opacity: 0; transform: translateY(-6px) scale(0.96); }
		to   { opacity: 1; transform: translateY(0)   scale(1); }
	}

	/* ── Header ───────────────────────────────────────────────────────────────── */
	.se-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 8px;
		margin-bottom: 10px;
	}

	.se-course-info {
		display: flex;
		flex-direction: column;
		gap: 2px;
		overflow: hidden;
		flex: 1;
	}

	.se-code {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.82rem;
		font-weight: 700;
		color: var(--ocean-bright);
	}

	.se-name {
		font-size: 0.72rem;
		color: var(--text-muted);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 200px;
	}

	.se-close {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 1px solid var(--border);
		background: var(--surface-raised);
		border-radius: 5px;
		width: 26px;
		height: 26px;
		cursor: pointer;
		color: var(--text-muted);
		transition: all 0.12s ease;
	}
	.se-close:hover {
		background: var(--danger-bg);
		border-color: var(--danger-border);
		color: var(--danger-text);
	}

	/* ── Capstone notice ──────────────────────────────────────────────────────── */
	.se-capstone-notice {
		display: flex;
		align-items: center;
		gap: 7px;
		background: var(--warn-bg);
		border: 1px solid var(--warn-border);
		border-radius: var(--radius-sm);
		padding: 7px 10px;
		font-size: 0.72rem;
		color: var(--warn-text);
		line-height: 1.4;
		margin-bottom: 10px;
	}

	/* ── Divider ──────────────────────────────────────────────────────────────── */
	.se-divider {
		height: 1px;
		background: var(--border-soft);
		margin-bottom: 10px;
	}

	/* ── Options grid ─────────────────────────────────────────────────────────── */
	.se-options {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 7px;
		margin-bottom: 9px;
	}

	.se-btn {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 4px;
		padding: 10px 6px;
		border-radius: var(--radius-sm);
		border: 1.5px solid;
		cursor: pointer;
		transition: all 0.14s ease;
		background: var(--surface-raised);
		line-height: 1;
	}
	.se-btn:hover:not(.se-active) { transform: translateY(-1px); filter: brightness(1.05); }

	.se-btn-icon { font-size: 1.1rem; }
	.se-btn-label {
		font-family: 'Raleway', sans-serif;
		font-size: 0.74rem;
		font-weight: 700;
		letter-spacing: 0.04em;
	}

	/* Inactive states */
	.se-lock    { border-color: var(--fb-lock-border);    color: var(--fb-lock-text); }
	.se-exclude { border-color: var(--fb-exclude-border); color: var(--fb-exclude-text); }
	.se-like    { border-color: var(--fb-like-border);    color: var(--fb-like-text); }
	.se-dislike { border-color: var(--fb-dislike-border); color: var(--fb-dislike-text); }

	/* Active states */
	.se-lock.se-active    { background: var(--fb-lock-bg);    border-color: var(--fb-lock-accent);    box-shadow: 0 0 14px rgba(0,255,133,0.40); }
	.se-exclude.se-active { background: var(--fb-exclude-bg); border-color: var(--fb-exclude-accent); box-shadow: 0 0 14px rgba(255,111,97,0.40); }
	.se-like.se-active    { background: var(--fb-like-bg);    border-color: var(--fb-like-accent);    box-shadow: 0 0 14px rgba(215,218,220,0.32); }
	.se-dislike.se-active { background: var(--fb-dislike-bg); border-color: var(--fb-dislike-accent); box-shadow: 0 0 14px rgba(218,165,32,0.44); }

	/* ── Clear button ────────────────────────────────────────────────────────── */
	.se-clear {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 6px;
		width: 100%;
		background: none;
		border: 1px solid var(--border);
		color: var(--text-muted);
		font-size: 0.73rem;
		font-family: 'Raleway', sans-serif;
		padding: 6px 8px;
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: all 0.12s ease;
	}
	.se-clear:hover {
		background: var(--danger-bg);
		border-color: var(--danger-border);
		color: var(--danger-text);
	}
</style>

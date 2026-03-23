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

	const POPUP_W = 264;
	const POPUP_H_MAX = 260;

	function popupStyle(rect: DOMRect | null): string {
		if (!rect) return 'display:none';
		let top = rect.bottom + 6;
		let left = rect.left;
		if (typeof window !== 'undefined') {
			if (left + POPUP_W > window.innerWidth - 8) {
				left = Math.max(8, window.innerWidth - POPUP_W - 8);
			}
			if (top + POPUP_H_MAX > window.innerHeight - 8) {
				top = Math.max(8, rect.top - POPUP_H_MAX - 6);
			}
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
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- Transparent full-screen overlay — catches outside clicks to close the popup. -->
<div class="se-overlay" role="presentation" onclick={handleOverlay}></div>

<!-- Floating card -->
<div class="se-popup" style={popupStyle(anchorRect)} role="dialog" aria-modal="true" aria-label="Slot feedback editor">
	<div class="se-header">
		<div class="se-course-info">
			<span class="se-code">{course?.course_code ?? ''}</span>
			<span class="se-name">{course?.course_name ?? ''}</span>
		</div>
		<button type="button" class="se-close" onclick={onClose} aria-label="Close slot editor">✕</button>
	</div>

	{#if isCapstone}
		<div class="se-capstone-notice">
			⚠ Applies to both capstone slots (4F and 4S)
		</div>
	{/if}

	<div class="se-options">
		<button
			type="button"
			class="se-btn se-lock"
			class:se-active={currentState === 'LOCK'}
			onclick={() => toggle('LOCK')}
			title="Course must appear in regenerated profile"
		>
			🔒 Lock
		</button>
		<button
			type="button"
			class="se-btn se-exclude"
			class:se-active={currentState === 'EXCLUDE'}
			onclick={() => toggle('EXCLUDE')}
			title="Course must not appear in regenerated profile"
		>
			❌ Exclude
		</button>
		<button
			type="button"
			class="se-btn se-like"
			class:se-active={currentState === 'LIKE'}
			onclick={() => toggle('LIKE')}
			title="Boost this course in the regenerated profile"
		>
			👍 Like
		</button>
		<button
			type="button"
			class="se-btn se-dislike"
			class:se-active={currentState === 'DISLIKE'}
			onclick={() => toggle('DISLIKE')}
			title="Discourage this course in the regenerated profile (best-effort)"
		>
			👎 Dislike
		</button>
	</div>

	{#if currentState}
		<button type="button" class="se-clear" onclick={() => onSet(null)}>
			Clear feedback for this slot
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
		background: #fff;
		border: 1px solid var(--border);
		border-radius: 14px;
		box-shadow: var(--shadow-md);
		padding: 13px;
		animation: se-in 0.12s ease;
	}

	@keyframes se-in {
		from { opacity: 0; transform: translateY(-4px) scale(0.97); }
		to   { opacity: 1; transform: translateY(0)   scale(1); }
	}

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
	}

	.se-code {
		font-weight: 700;
		font-size: 0.88rem;
		color: var(--text);
	}

	.se-name {
		font-size: 0.72rem;
		color: var(--text-muted);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 190px;
	}

	.se-close {
		flex-shrink: 0;
		border: 1px solid var(--border);
		background: #f8faff;
		border-radius: 7px;
		width: 26px;
		height: 26px;
		cursor: pointer;
		font-size: 0.72rem;
		display: grid;
		place-items: center;
		color: var(--text-muted);
		transition: background 0.1s;
	}
	.se-close:hover { background: #eef3ff; }

	.se-capstone-notice {
		background: #fef9c3;
		border: 1px solid #fde68a;
		border-radius: 8px;
		padding: 6px 8px;
		font-size: 0.72rem;
		color: #78350f;
		margin-bottom: 10px;
		line-height: 1.4;
	}

	.se-options {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 6px;
		margin-bottom: 8px;
	}

	.se-btn {
		border: 1.5px solid;
		border-radius: 8px;
		padding: 8px 6px;
		font-size: 0.78rem;
		cursor: pointer;
		font-weight: 500;
		background: #f8faff;
		transition: background 0.12s, border-color 0.12s, transform 0.08s;
		text-align: center;
		line-height: 1.2;
	}
	.se-btn:hover { opacity: 0.88; transform: scale(0.98); }

	/* Default (inactive) border colours */
	.se-lock    { border-color: #93c5fd; color: #1d4ed8; }
	.se-exclude { border-color: #fca5a5; color: #b91c1c; }
	.se-like    { border-color: #86efac; color: #15803d; }
	.se-dislike { border-color: #fdba74; color: #c2410c; }

	/* Active (selected) states */
	.se-lock.se-active    { background: #dbeafe; border-color: #3b82f6; font-weight: 700; }
	.se-exclude.se-active { background: #fee2e2; border-color: #ef4444; font-weight: 700; }
	.se-like.se-active    { background: #dcfce7; border-color: #22c55e; font-weight: 700; }
	.se-dislike.se-active { background: #ffedd5; border-color: #f97316; font-weight: 700; }

	.se-clear {
		width: 100%;
		border: 1px solid var(--border);
		background: none;
		color: var(--text-muted);
		font-size: 0.72rem;
		padding: 5px 8px;
		border-radius: 7px;
		cursor: pointer;
		transition: background 0.1s;
		text-align: center;
	}
	.se-clear:hover { background: #f8faff; }
</style>

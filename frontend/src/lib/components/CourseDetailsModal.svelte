<script lang="ts">
	import type { CourseInfo } from '$lib/types/profile';

	let { course, onClose }: { course: CourseInfo | null; onClose: () => void } = $props();

	function handleOverlay(event: MouseEvent) {
		if (event.target === event.currentTarget) onClose();
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') onClose();
	}

	function formatCourseType(value: string | null | undefined): string {
		if (!value) return 'N/A';
		return value.replace('_', '-').replace(/^\w/, c => c.toUpperCase());
	}

	function formatNonTechnical(value: string | null | undefined): string {
		if (!value) return 'N/A';
		const n = value.toLowerCase();
		if (n === 'hss') return 'HSS';
		if (n === 'cs') return 'CS';
		return n.charAt(0).toUpperCase() + n.slice(1);
	}

	function areaLabel(area: number): string {
		return area === -1 ? 'N/A' : `Area ${area}`;
	}
</script>

<svelte:window onkeydown={handleKeydown} />

{#if course}
	<div
		class="modal-overlay"
		role="presentation"
		onclick={handleOverlay}
	>
		<div
			class="modal-card"
			role="dialog"
			aria-modal="true"
			aria-label="Course details for {course.course_code}"
		>
			<!-- Header -->
			<div class="modal-header">
				<div class="modal-title-block">
					<div class="modal-code">{course.course_code}</div>
					<h3 class="modal-name">{course.course_name}</h3>
				</div>
				<button
					type="button"
					class="modal-close"
					onclick={onClose}
					aria-label="Close course details"
				>
					<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
						<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
					</svg>
				</button>
			</div>

			<!-- Gold divider -->
			<div class="modal-divider" aria-hidden="true"></div>

			<!-- Description -->
			<p class="modal-desc">{course.course_description || 'No description available for this course.'}</p>

			<!-- Key attributes -->
			<h4 class="meta-heading">Course Details</h4>
			<div class="meta-grid">
				<div class="meta-item">
					<span class="meta-label">Area</span>
					<strong class="meta-value">{areaLabel(course.area)}</strong>
				</div>
				<div class="meta-item">
					<span class="meta-label">Term</span>
					<strong class="meta-value">{course.term || 'N/A'}</strong>
				</div>
				<div class="meta-item">
					<span class="meta-label">Credits</span>
					<strong class="meta-value">{course.num_credits}</strong>
				</div>
				<div class="meta-item">
					<span class="meta-label">Type</span>
					<strong class="meta-value">{formatCourseType(course.course_type)}</strong>
				</div>
				<div class="meta-item">
					<span class="meta-label">Kernel</span>
					<strong class="meta-value meta-{course.kernel_course ? 'yes' : 'no'}">{course.kernel_course ? 'Yes' : 'No'}</strong>
				</div>
				<div class="meta-item">
					<span class="meta-label">Tech Elective</span>
					<strong class="meta-value meta-{course.technical_elective ? 'yes' : 'no'}">{course.technical_elective ? 'Yes' : 'No'}</strong>
				</div>
				<div class="meta-item">
					<span class="meta-label">Free Elective</span>
					<strong class="meta-value meta-{course.free_elective ? 'yes' : 'no'}">{course.free_elective ? 'Yes' : 'No'}</strong>
				</div>
				<div class="meta-item">
					<span class="meta-label">Non-tech</span>
					<strong class="meta-value">{formatNonTechnical(course.non_technical_type)}</strong>
				</div>
			</div>

			<!-- CEAB Attributes -->
			<h4 class="meta-heading">CEAB Academic Units</h4>
			<div class="ceab-grid">
				{#each [
					{ label: 'Mathematics', value: course.ceab_math ?? 0 },
					{ label: 'Natural Sci.', value: course.ceab_ns ?? 0 },
					{ label: 'Comp. Studies', value: course.ceab_cs ?? 0 },
					{ label: 'Eng. Science', value: course.ceab_es ?? 0 },
					{ label: 'Eng. Design', value: course.ceab_ed ?? 0 },
				] as attr}
					<div class="ceab-item">
						<span class="ceab-label">{attr.label}</span>
						<strong class="ceab-value {attr.value > 0 ? 'ceab-nonzero' : ''}">{attr.value.toFixed(1)}</strong>
					</div>
				{/each}
			</div>
		</div>
	</div>
{/if}

<style>
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(6, 15, 30, 0.75);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 20px;
		z-index: 1000;
		backdrop-filter: blur(4px);
		animation: fade-in 0.18s ease;
	}

	:global([data-theme='light']) .modal-overlay {
		background: rgba(26, 39, 68, 0.55);
	}

	.modal-card {
		width: min(720px, 100%);
		max-height: 88vh;
		overflow-y: auto;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-lg), var(--glow-ocean);
		padding: 22px;
		animation: fade-in 0.22s ease;
	}

	/* ── Header ───────────────────────────────────────────────────────────────── */
	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 12px;
	}

	.modal-title-block { flex: 1; min-width: 0; }

	.modal-code {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.8rem;
		font-weight: 700;
		color: var(--ocean-bright);
		letter-spacing: 0.08em;
		margin-bottom: 4px;
		background: rgba(32, 119, 178, 0.12);
		border: 1px solid rgba(32, 119, 178, 0.25);
		border-radius: 4px;
		padding: 2px 8px;
		display: inline-block;
	}

	.modal-name {
		font-family: 'Cinzel', serif;
		font-size: 1.1rem;
		font-weight: 600;
		color: var(--text);
		margin: 0;
		letter-spacing: 0.03em;
		line-height: 1.3;
	}

	.modal-close {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border: 1px solid var(--border);
		background: var(--surface-raised);
		border-radius: var(--radius-sm);
		color: var(--text-muted);
		cursor: pointer;
		transition: all 0.15s ease;
	}
	.modal-close:hover {
		background: var(--danger-bg);
		border-color: var(--danger-border);
		color: var(--danger-text);
	}

	/* ── Divider ──────────────────────────────────────────────────────────────── */
	.modal-divider {
		height: 1px;
		background: linear-gradient(90deg, var(--gold-dim), var(--ocean-dim), transparent);
		opacity: 0.4;
		margin: 14px 0;
	}

	/* ── Description ─────────────────────────────────────────────────────────── */
	.modal-desc {
		font-size: 0.87rem;
		color: var(--text-muted);
		line-height: 1.65;
		margin: 0 0 18px;
	}

	/* ── Section headings ────────────────────────────────────────────────────── */
	.meta-heading {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.68rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.14em;
		color: var(--gold);
		margin: 0 0 10px;
		padding-bottom: 6px;
		border-bottom: 1px solid var(--border-soft);
	}

	/* ── Meta grid ───────────────────────────────────────────────────────────── */
	.meta-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 7px;
		margin-bottom: 18px;
	}

	.meta-item {
		background: var(--surface-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 9px 12px;
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 8px;
	}

	.meta-label {
		font-size: 0.73rem;
		color: var(--text-muted);
		font-weight: 500;
	}

	.meta-value {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.82rem;
		color: var(--text);
		font-weight: 700;
	}
	.meta-yes { color: var(--success-text); }
	.meta-no  { color: var(--text-faint); }

	/* ── CEAB grid ───────────────────────────────────────────────────────────── */
	.ceab-grid {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 7px;
	}

	.ceab-item {
		background: var(--surface-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 9px 12px;
		display: flex;
		flex-direction: column;
		gap: 3px;
	}

	.ceab-label {
		font-size: 0.7rem;
		color: var(--text-muted);
		font-weight: 500;
	}

	.ceab-value {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.95rem;
		font-weight: 700;
		color: var(--text-faint);
	}
	.ceab-nonzero { color: var(--gold); }

	/* ── Responsive ──────────────────────────────────────────────────────────── */
	@media (max-width: 600px) {
		.meta-grid { grid-template-columns: 1fr; }
		.ceab-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
	}
</style>

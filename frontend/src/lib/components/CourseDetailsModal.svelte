<script lang="ts">
	import type { CourseInfo } from '$lib/types/profile';

	let { course, onClose }: { course: CourseInfo | null; onClose: () => void } = $props();

	function handleOverlay(event: MouseEvent) {
		if (event.target === event.currentTarget) onClose();
	}

	function formatCourseType(value: string | null | undefined): string {
		if (!value) return 'N/A';
		const normalized = value.replace('_', '-').toLowerCase();
		return normalized.charAt(0).toUpperCase() + normalized.slice(1);
	}

	function formatNonTechnical(value: string | null | undefined): string {
		if (!value) return 'N/A';
		const normalized = value.toLowerCase();
		if (normalized === 'hss') return 'HSS';
		if (normalized === 'cs') return 'CS';
		return normalized.charAt(0).toUpperCase() + normalized.slice(1);
	}
</script>

{#if course}
	<div class="modal-overlay" role="presentation" onclick={handleOverlay}>
		<div class="modal-card" role="dialog" aria-modal="true" aria-label="Course details">
			<div class="modal-header">
				<div>
					<h3>{course.course_code}</h3>
					<p>{course.course_name}</p>
				</div>
				<button type="button" class="modal-close" onclick={onClose} aria-label="Close">x</button>
			</div>
			<p class="desc">{course.course_description || 'Description not available.'}</p>
			<div class="meta">
				<div><span>Area</span><strong>{course.area === -1 ? 'N/A' : course.area}</strong></div>
				<div><span>Term</span><strong>{course.term || 'N/A'}</strong></div>
				<div><span>Credits</span><strong>{course.num_credits}</strong></div>
				<div><span>Type</span><strong>{formatCourseType(course.course_type)}</strong></div>
				<div><span>Kernel</span><strong>{course.kernel_course ? 'Yes' : 'No'}</strong></div>
				<div><span>Tech Elective</span><strong>{course.technical_elective ? 'Yes' : 'No'}</strong></div>
				<div><span>Free Elective</span><strong>{course.free_elective ? 'Yes' : 'No'}</strong></div>
				<div><span>Non-tech</span><strong>{formatNonTechnical(course.non_technical_type)}</strong></div>
			</div>
			<h4>CEAB Attributes</h4>
			<div class="meta ceab">
				<div><span>Math</span><strong>{(course.ceab_math ?? 0).toFixed(1)}</strong></div>
				<div><span>NS</span><strong>{(course.ceab_ns ?? 0).toFixed(1)}</strong></div>
				<div><span>CS</span><strong>{(course.ceab_cs ?? 0).toFixed(1)}</strong></div>
				<div><span>ES</span><strong>{(course.ceab_es ?? 0).toFixed(1)}</strong></div>
				<div><span>ED</span><strong>{(course.ceab_ed ?? 0).toFixed(1)}</strong></div>
			</div>
		</div>
	</div>
{/if}

<style>
	.modal-overlay { position: fixed; inset: 0; background: rgba(15,23,42,.6); display:flex; align-items:center; justify-content:center; padding:20px; z-index:1000; }
	.modal-card { width:min(760px,100%); max-height:85vh; overflow:auto; background:#fff; border-radius:14px; border:1px solid var(--border); box-shadow: var(--shadow-md); padding:16px; }
	.modal-header { display:flex; justify-content:space-between; gap:8px; }
	.modal-header h3 { margin:0; font-size:1.1rem; }
	.modal-header p { margin:4px 0 0; color:var(--text-muted); }
	.modal-close { border:1px solid var(--border); background:#f8faff; border-radius:8px; width:30px; height:30px; cursor:pointer; font-weight:700; }
	.desc { line-height:1.5; color:var(--text-muted); }
	.meta { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; }
	.meta > div { background:#f8faff; border:1px solid var(--border); border-radius:10px; padding:8px 10px; display:flex; justify-content:space-between; gap:10px; }
	span { color:var(--text-muted); font-size:.8rem; }
	h4 { margin:12px 0 8px; font-size:.9rem; }
	.ceab { grid-template-columns: repeat(3,minmax(0,1fr)); }
	@media (max-width:900px){ .meta, .ceab{ grid-template-columns:1fr; } }
</style>

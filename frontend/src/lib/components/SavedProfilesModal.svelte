<script lang="ts">
	import { onMount } from 'svelte';
	import type { SupabaseClient } from '@supabase/supabase-js';
	import type { ProfileResponse } from '$lib/types/profile';
	import type { FeedbackRecord } from '$lib/types/feedback';
	import {
		listSavedProfiles,
		saveProfile,
		deleteSavedProfile,
		SAVE_LIMIT,
		type SavedProfile
	} from '$lib/api/savedProfiles';

	export let supabase: SupabaseClient;
	export let currentProfile: ProfileResponse | null = null;
	export let currentFeedback: FeedbackRecord = {};
	export let originalPreferences: string[] = [];
	export let year12Choice: string = 'ECE297H1';
	export let interests: string = '';
	export let onLoad: (saved: SavedProfile) => void;
	export let onClose: () => void;

	let profiles: SavedProfile[] = [];
	let loadingList = true;
	let saveName = '';
	let saving = false;
	let saveError: string | null = null;
	let saveSuccess = false;
	let confirmLoadId: string | null = null;
	let deletingId: string | null = null;

	onMount(async () => {
		await refresh();
	});

	async function refresh() {
		loadingList = true;
		profiles = await listSavedProfiles(supabase);
		loadingList = false;
	}

	async function handleSave() {
		if (!saveName.trim() || !currentProfile) return;
		saving = true;
		saveError = null;
		saveSuccess = false;
		const result = await saveProfile(
			supabase,
			saveName.trim(),
			currentProfile,
			originalPreferences,
			currentFeedback,
			year12Choice,
			interests
		);
		if (result.error) {
			saveError = result.error;
		} else {
			saveSuccess = true;
			saveName = '';
			await refresh();
			setTimeout(() => (saveSuccess = false), 3000);
		}
		saving = false;
	}

	async function handleDelete(id: string) {
		deletingId = id;
		await deleteSavedProfile(supabase, id);
		deletingId = null;
		await refresh();
	}

	function requestLoad(saved: SavedProfile) {
		if (currentProfile) {
			confirmLoadId = saved.id;
		} else {
			onLoad(saved);
			onClose();
		}
	}

	function confirmLoad() {
		const saved = profiles.find((p) => p.id === confirmLoadId);
		if (saved) {
			onLoad(saved);
			onClose();
		}
		confirmLoadId = null;
	}

	function formatDate(iso: string) {
		return new Date(iso).toLocaleDateString(undefined, {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') onClose();
	}
</script>

<svelte:window on:keydown={handleKeydown} />

<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
<div class="backdrop" on:click|self={onClose} role="dialog" aria-modal="true" aria-label="Saved Profiles" tabindex="-1">
	<div class="modal">
		<!-- Header -->
		<div class="modal-header">
			<h2 class="modal-title">Cloud Profiles</h2>
			<button type="button" class="btn-close" on:click={onClose} aria-label="Close modal">✕</button>
		</div>

		<!-- Save current profile -->
		{#if currentProfile}
			<div class="save-section">
				<h3 class="section-label">Save Current Profile</h3>
				<div class="save-row">
					<input
						type="text"
						class="save-input"
						bind:value={saveName}
						placeholder="e.g. ML-focused plan, Signal Processing focus…"
						maxlength="60"
						disabled={saving}
						on:keydown={(e) => e.key === 'Enter' && handleSave()}
					/>
					<button
						type="button"
						class="btn-save"
						disabled={!saveName.trim() || saving || profiles.length >= SAVE_LIMIT}
						on:click={handleSave}
					>
						{saving ? 'Saving…' : 'Save'}
					</button>
				</div>
				{#if saveError}
					<p class="save-error">{saveError}</p>
				{/if}
				{#if saveSuccess}
					<p class="save-success">Profile saved successfully.</p>
				{/if}
				<p class="save-count">
					{profiles.length} / {SAVE_LIMIT} saves used
				</p>
			</div>
		{/if}

		<!-- Saved profiles list -->
		<div class="list-section">
			<h3 class="section-label">Your Saved Profiles</h3>
			{#if loadingList}
				<p class="list-empty">Loading…</p>
			{:else if profiles.length === 0}
				<p class="list-empty">
					No saved profiles yet.
					{#if currentProfile}
						Generate a profile above and save it with a name.
					{:else}
						Generate a profile first, then save it here.
					{/if}
				</p>
			{:else}
				<div class="profile-list">
					{#each profiles as saved (saved.id)}
						<div class="profile-row">
							<div class="profile-info">
								<span class="profile-name">{saved.name}</span>
								<span class="profile-meta">
									{formatDate(saved.saved_at)}
									{#if saved.year12_choice}
										· {saved.year12_choice}
									{/if}
								</span>
								{#if saved.interests}
									<span class="profile-interests" title={saved.interests}>
										{saved.interests.length > 70
											? saved.interests.slice(0, 70) + '…'
											: saved.interests}
									</span>
								{/if}
							</div>
							<div class="profile-actions">
								<button
									type="button"
									class="btn-load-profile"
									on:click={() => requestLoad(saved)}
								>
									Load
								</button>
								<button
									type="button"
									class="btn-delete-profile"
									disabled={deletingId === saved.id}
									on:click={() => handleDelete(saved.id)}
									aria-label="Delete {saved.name}"
								>
									{deletingId === saved.id ? '…' : '✕'}
								</button>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Confirmation dialog overlay -->
		{#if confirmLoadId}
			<div class="confirm-overlay">
				<div class="confirm-box">
					<p class="confirm-msg">
						Loading this profile will replace your current unsaved work. Continue?
					</p>
					<div class="confirm-actions">
						<button
							type="button"
							class="btn-cancel"
							on:click={() => (confirmLoadId = null)}
						>
							Cancel
						</button>
						<button type="button" class="btn-confirm" on:click={confirmLoad}>
							Load Profile
						</button>
					</div>
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.55);
		z-index: 200;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 16px;
		animation: fade-in 0.2s ease;
	}

	@keyframes fade-in {
		from { opacity: 0; }
		to { opacity: 1; }
	}

	.modal {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		box-shadow: 0 8px 40px rgba(0, 0, 0, 0.45);
		width: 100%;
		max-width: 560px;
		max-height: 88vh;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		position: relative;
		animation: slide-up 0.22s ease;
	}

	@keyframes slide-up {
		from { transform: translateY(14px); opacity: 0; }
		to { transform: translateY(0); opacity: 1; }
	}

	/* Header */
	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px 20px;
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.modal-title {
		font-family: 'Cinzel', serif;
		font-size: 1.05rem;
		font-weight: 700;
		letter-spacing: 0.06em;
		color: var(--gold);
		margin: 0;
	}

	.btn-close {
		background: none;
		border: 1px solid var(--border);
		border-radius: 5px;
		color: var(--text-faint);
		font-size: 0.85rem;
		padding: 3px 8px;
		cursor: pointer;
		transition: all 0.12s ease;
	}
	.btn-close:hover {
		background: var(--danger-bg);
		border-color: var(--danger-border);
		color: var(--danger-text);
	}

	/* Section label */
	.section-label {
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--text-muted);
		margin: 0 0 10px;
	}

	/* Save section */
	.save-section {
		padding: 16px 20px;
		border-bottom: 1px solid var(--border-soft);
		background: var(--surface-soft);
	}

	.save-row {
		display: flex;
		gap: 8px;
	}

	.save-input {
		flex: 1;
		background: var(--surface-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		color: var(--text);
		font-family: 'Raleway', sans-serif;
		font-size: 0.88rem;
		padding: 8px 12px;
		transition: border-color 0.15s;
	}
	.save-input:focus {
		outline: none;
		border-color: var(--ocean-light);
		box-shadow: 0 0 0 3px rgba(32, 119, 178, 0.16);
	}
	.save-input::placeholder { color: var(--text-faint); }
	.save-input:disabled { opacity: 0.6; }

	.btn-save {
		padding: 8px 16px;
		border-radius: var(--radius-sm);
		border: 1px solid var(--ocean);
		background: rgba(32, 119, 178, 0.18);
		color: var(--ocean-bright);
		font-size: 0.84rem;
		font-weight: 700;
		cursor: pointer;
		transition: all 0.15s ease;
		white-space: nowrap;
	}
	.btn-save:hover:not(:disabled) {
		background: rgba(32, 119, 178, 0.3);
	}
	.btn-save:disabled { opacity: 0.45; cursor: not-allowed; }

	.save-error {
		font-size: 0.8rem;
		color: var(--danger-text);
		margin: 6px 0 0;
	}
	.save-success {
		font-size: 0.8rem;
		color: var(--success-text);
		margin: 6px 0 0;
	}
	.save-count {
		font-size: 0.75rem;
		color: var(--text-faint);
		margin: 6px 0 0;
		font-family: 'JetBrains Mono', monospace;
	}

	/* List section */
	.list-section {
		padding: 16px 20px;
		flex: 1;
	}

	.list-empty {
		font-size: 0.84rem;
		color: var(--text-muted);
		margin: 0;
		line-height: 1.6;
	}

	.profile-list {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.profile-row {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 12px;
		padding: 10px 12px;
		background: var(--surface-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		transition: border-color 0.15s;
	}
	.profile-row:hover {
		border-color: var(--ocean-dim);
	}

	.profile-info {
		display: flex;
		flex-direction: column;
		gap: 3px;
		min-width: 0;
		flex: 1;
	}

	.profile-name {
		font-weight: 700;
		font-size: 0.9rem;
		color: var(--text);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.profile-meta {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.7rem;
		color: var(--text-faint);
	}

	.profile-interests {
		font-size: 0.78rem;
		color: var(--text-muted);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-style: italic;
	}

	.profile-actions {
		display: flex;
		gap: 6px;
		flex-shrink: 0;
		align-items: center;
	}

	.btn-load-profile {
		padding: 5px 12px;
		border-radius: var(--radius-sm);
		border: 1px solid var(--ocean);
		background: rgba(32, 119, 178, 0.12);
		color: var(--ocean-bright);
		font-size: 0.78rem;
		font-weight: 700;
		cursor: pointer;
		transition: all 0.14s ease;
		white-space: nowrap;
	}
	.btn-load-profile:hover {
		background: rgba(32, 119, 178, 0.24);
	}

	.btn-delete-profile {
		padding: 5px 8px;
		border-radius: var(--radius-sm);
		border: 1px solid var(--border);
		background: none;
		color: var(--text-faint);
		font-size: 0.78rem;
		cursor: pointer;
		transition: all 0.12s ease;
		min-width: 28px;
		text-align: center;
	}
	.btn-delete-profile:hover:not(:disabled) {
		background: var(--danger-bg);
		border-color: var(--danger-border);
		color: var(--danger-text);
	}
	.btn-delete-profile:disabled { opacity: 0.4; cursor: not-allowed; }

	/* Confirm overlay */
	.confirm-overlay {
		position: absolute;
		inset: 0;
		background: rgba(0, 0, 0, 0.6);
		border-radius: var(--radius);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 20px;
	}

	.confirm-box {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 20px;
		max-width: 340px;
		box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
	}

	.confirm-msg {
		font-size: 0.9rem;
		color: var(--text);
		margin: 0 0 16px;
		line-height: 1.6;
	}

	.confirm-actions {
		display: flex;
		gap: 8px;
		justify-content: flex-end;
	}

	.btn-cancel {
		padding: 7px 14px;
		border-radius: var(--radius-sm);
		border: 1px solid var(--border);
		background: var(--surface-raised);
		color: var(--text-muted);
		font-size: 0.84rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.14s;
	}
	.btn-cancel:hover { background: var(--surface-hover); }

	.btn-confirm {
		padding: 7px 14px;
		border-radius: var(--radius-sm);
		border: 1px solid var(--ocean);
		background: rgba(32, 119, 178, 0.2);
		color: var(--ocean-bright);
		font-size: 0.84rem;
		font-weight: 700;
		cursor: pointer;
		transition: all 0.14s;
	}
	.btn-confirm:hover { background: rgba(32, 119, 178, 0.35); }
</style>

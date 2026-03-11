import { env } from '$env/dynamic/public';
import type { GenerateProfilePayload, ProfileResponse } from '$lib/types/profile';

const API_BASE_URL = env.PUBLIC_API_BASE_URL || 'http://localhost:8000';

function toMessage(status: number, detail: unknown): string {
	if (typeof detail === 'string' && detail.trim()) {
		return detail;
	}

	if (status === 429) {
		return 'Too many requests. Please wait a moment and try again.';
	}

	return 'Failed to generate profile. Make sure backend is running and configured.';
}

export async function generateProfile(payload: GenerateProfilePayload): Promise<ProfileResponse> {
	const response = await fetch(`${API_BASE_URL}/generate-profile`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(payload)
	});

	const data = (await response.json().catch(() => ({}))) as ProfileResponse & { detail?: unknown };

	if (!response.ok) {
		throw new Error(toMessage(response.status, data.detail));
	}

	return data;
}

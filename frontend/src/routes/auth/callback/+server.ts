import { redirect } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ url, locals: { supabase } }) => {
	const code = url.searchParams.get('code');
	const next = url.searchParams.get('next') ?? '/options';

	if (code) {
		const { error } = await supabase.auth.exchangeCodeForSession(code);
		if (!error) {
			// Redirect to intended destination after successful OAuth exchange.
			redirect(303, `/${next.slice(1)}`);
		}
	}

	// Auth failed — redirect back to sign-in with an error hint.
	redirect(303, '/signin?error=auth_callback_failed');
};

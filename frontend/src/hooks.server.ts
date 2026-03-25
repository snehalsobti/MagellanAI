import { createServerClient } from '@supabase/ssr';
import { redirect, type Handle } from '@sveltejs/kit';
import { sequence } from '@sveltejs/kit/hooks';
import { PUBLIC_SUPABASE_URL, PUBLIC_SUPABASE_ANON_KEY } from '$env/static/public';

const PUBLIC_PATHS = ['/signin', '/auth/callback', '/auth/confirm'];

function isPublicPath(pathname: string): boolean {
	return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + '/'));
}

const supabaseHandle: Handle = async ({ event, resolve }) => {
	event.locals.supabase = createServerClient(PUBLIC_SUPABASE_URL, PUBLIC_SUPABASE_ANON_KEY, {
		cookies: {
			getAll: () => event.cookies.getAll(),
			setAll: (cookiesToSet) => {
				cookiesToSet.forEach(({ name, value, options }) => {
					event.cookies.set(name, value, { ...options, path: '/' });
				});
			}
		}
	});

	event.locals.safeGetSession = async () => {
		const {
			data: { session }
		} = await event.locals.supabase.auth.getSession();
		if (!session) return { session: null, user: null };

		// Validate the token is still valid against Supabase (prevents JWT forgery).
		const {
			data: { user },
			error
		} = await event.locals.supabase.auth.getUser();
		if (error || !user) return { session: null, user: null };
		// Spread session but override the user with the server-validated copy.
		return { session: { ...session, user }, user };
	};

	return resolve(event, {
		filterSerializedResponseHeaders(name) {
			return name === 'content-range' || name === 'x-supabase-api-version';
		}
	});
};

const authGuardHandle: Handle = async ({ event, resolve }) => {
	if (!isPublicPath(event.url.pathname)) {
		const { session } = await event.locals.safeGetSession();
		if (!session) {
			redirect(303, '/signin');
		}
	}
	return resolve(event);
};

export const handle = sequence(supabaseHandle, authGuardHandle);

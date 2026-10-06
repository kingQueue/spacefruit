import { supabase } from "./supabase";

export async function authFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const { data: { session } = {} } = supabase ? await supabase.auth.getSession() : {};
  if (session?.access_token) headers.Authorization = `Bearer ${session.access_token}`;
  return fetch(path, { credentials: "same-origin", ...options, headers });
}

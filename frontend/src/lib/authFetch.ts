/**
 * Authenticated fetch wrapper for API calls.
 *
 * Uses Clerk's session to get a JWT token and attach it as
 * an Authorization: Bearer header on every request.
 *
 * When Clerk is not configured (dev mode), falls back to
 * regular fetch without auth headers.
 */

let _getTokenFn: (() => Promise<string | null>) | null = null;
const _authListeners = new Set<() => void>();

/**
 * Register Clerk's getToken function so the API layer can
 * attach auth headers without React hooks.
 *
 * Call this once from a React component that has access to useAuth():
 *   const { getToken } = useAuth();
 *   setAuthTokenProvider(getToken);
 */
export function setAuthTokenProvider(getToken: (() => Promise<string | null>) | null) {
  _getTokenFn = getToken;
  _authListeners.forEach((fn) => {
    try {
      fn();
    } catch (err) {
      console.error("[authFetch] Listener error:", err);
    }
  });
}

/**
 * Subscribe to auth token / sign-in state changes.
 * Returns an unsubscribe cleanup function.
 */
export function onAuthChange(listener: () => void): () => void {
  _authListeners.add(listener);
  return () => {
    _authListeners.delete(listener);
  };
}

/**
 * Get the current auth headers.
 * Returns an empty object if Clerk is not configured or user is logged out.
 */
async function getAuthHeaders(): Promise<Record<string, string>> {
  if (!_getTokenFn) return {};
  try {
    const token = await _getTokenFn();
    if (token) {
      return { Authorization: `Bearer ${token}` };
    }
  } catch {
    // Clerk not available — dev mode
  }
  return {};
}

/**
 * Authenticated fetch — drop-in replacement for window.fetch
 * that automatically attaches the Clerk JWT.
 */
export async function authFetch(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> {
  const authHeaders = await getAuthHeaders();
  const mergedHeaders = {
    ...authHeaders,
    ...(init?.headers instanceof Headers
      ? Object.fromEntries(init.headers.entries())
      : (init?.headers as Record<string, string>) || {}),
  };

  return fetch(input, {
    ...init,
    headers: mergedHeaders,
  });
}

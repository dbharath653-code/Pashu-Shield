/**
 * Central API auth for every same-origin `/api/...` fetch:
 *  - attaches `Authorization: Bearer <access token>` when the caller did not set one;
 *  - on 401, performs a single refresh-token rotation (POST /api/v1/auth/refresh) and retries;
 *  - if refresh fails, clears the session and emits `pashu_auth_expired`.
 * Installed once from main.tsx so existing fetch() call sites keep working unchanged.
 */
const ACCESS_KEY = "auth_token";
const REFRESH_KEY = "auth_refresh_token";
const USER_KEY = "auth_user";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function storeSession(data: { access_token: string; refresh_token?: string; user?: unknown }): void {
  localStorage.setItem(ACCESS_KEY, data.access_token);
  if (data.refresh_token) localStorage.setItem(REFRESH_KEY, data.refresh_token);
  if (data.user) localStorage.setItem(USER_KEY, JSON.stringify(data.user));
}

export function clearSession(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
}

/** Extracts a human-readable message from the backend error envelope. */
export function apiErrorMessage(data: any, fallback: string): string {
  if (!data) return fallback;
  if (data.error?.message) return data.error.message;
  if (typeof data.detail === "string") return data.detail;
  if (data.detail?.message) return data.detail.message;
  return fallback;
}

function isApiUrl(input: RequestInfo | URL): boolean {
  const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
  if (url.startsWith("/api/")) return true;
  try {
    const u = new URL(url, window.location.href);
    return u.origin === window.location.origin && u.pathname.startsWith("/api/");
  } catch {
    return false;
  }
}

let refreshing: Promise<boolean> | null = null;

async function refreshOnce(nativeFetch: typeof fetch): Promise<boolean> {
  const rt = localStorage.getItem(REFRESH_KEY);
  if (!rt) return false;
  if (!refreshing) {
    refreshing = (async () => {
      try {
        const res = await nativeFetch("/api/v1/auth/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: rt }),
        });
        if (!res.ok) return false;
        storeSession(await res.json());
        return true;
      } catch {
        return false;
      } finally {
        setTimeout(() => (refreshing = null), 0);
      }
    })();
  }
  return refreshing;
}

export function installApiAuth(): void {
  const w = window as any;
  if (w.__pashuApiAuthInstalled) return;
  w.__pashuApiAuthInstalled = true;
  const nativeFetch = window.fetch.bind(window);

  window.fetch = async (input: RequestInfo | URL, init: RequestInit = {}) => {
    if (!isApiUrl(input)) return nativeFetch(input, init);
    const withAuth = (): RequestInit => {
      const headers = new Headers(init.headers || (input instanceof Request ? input.headers : undefined));
      const token = getAccessToken();
      if (token && !headers.has("Authorization")) headers.set("Authorization", `Bearer ${token}`);
      return { ...init, headers };
    };
    let res = await nativeFetch(input, withAuth());
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (res.status === 401 && !url.includes("/auth/")) {
      if (await refreshOnce(nativeFetch)) {
        res = await nativeFetch(input, withAuth());
      } else if (getAccessToken()) {
        clearSession();
        window.dispatchEvent(new CustomEvent("pashu_auth_expired"));
      }
    }
    return res;
  };
}

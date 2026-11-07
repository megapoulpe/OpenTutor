import { API_BASE } from "./api/client";

export function saveSession(tokens: { access_token: string; refresh_token: string }) {
  sessionStorage.setItem("access_token", tokens.access_token);
  sessionStorage.setItem("refresh_token", tokens.refresh_token);
}

export function clearSession() {
  sessionStorage.removeItem("access_token");
  sessionStorage.removeItem("refresh_token");
  sessionStorage.removeItem("opentutor-user-id");
}

let refreshing: Promise<boolean> | null = null;
export async function renewSession(): Promise<boolean> {
  if (refreshing) return refreshing;
  const token = sessionStorage.getItem("refresh_token");
  if (!token) return false;
  refreshing = (async () => {
    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: token }),
      });
      if (!response.ok) {
        if (response.status === 401 || response.status === 400) clearSession();
        return false;
      }
      saveSession(await response.json());
      return true;
    } catch { return false; }
    finally { refreshing = null; }
  })();
  return refreshing;
}

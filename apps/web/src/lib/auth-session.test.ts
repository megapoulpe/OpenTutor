import { beforeEach, describe, expect, it, vi } from "vitest";
import { clearSession, saveSession, renewSession } from "./auth-session";

describe("private sessions", () => {
  beforeEach(() => { sessionStorage.clear(); vi.restoreAllMocks(); });
  it("stores credentials in the current browser session", () => {
    saveSession({ access_token: "access", refresh_token: "refresh" });
    expect(sessionStorage.getItem("access_token")).toBe("access");
    clearSession();
    expect(sessionStorage.getItem("access_token")).toBeNull();
  });
  it("rotates refresh credentials and clears expired sessions", async () => {
    saveSession({ access_token: "old", refresh_token: "refresh" });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ access_token: "new", refresh_token: "rotated" }))));
    expect(await renewSession()).toBe(true);
    expect(sessionStorage.getItem("refresh_token")).toBe("rotated");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 401 })));
    expect(await renewSession()).toBe(false);
    expect(sessionStorage.getItem("access_token")).toBeNull();
  });
});

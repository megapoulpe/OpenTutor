import { beforeEach, describe, expect, it, vi } from "vitest";
import { getReviewSession } from "./progress";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

const flags = { loom: false, lector: false, cat_pretest: false, browser: false, vision: false, notion_export: false };
const session = { course_id: "course-1", items: [], count: 0 };
const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { "Content-Type": "application/json" },
});

describe("semantic review availability", () => {
  beforeEach(() => { mockFetch.mockReset(); });

  it("returns an empty session without calling the disabled LECTOR endpoint", async () => {
    mockFetch.mockImplementation(async (url: string) => url.endsWith("/features")
      ? json(flags)
      : json({ detail: "LECTOR semantic review is experimental" }, 404));

    await expect(getReviewSession("course-1", 5)).resolves.toEqual(session);
    expect(mockFetch.mock.calls.map(([url]) => url)).toEqual([expect.stringContaining("/features")]);
  });

  it("loads reviews with the requested limit when LECTOR is enabled", async () => {
    mockFetch.mockImplementation(async (url: string) => url.endsWith("/features")
      ? json({ ...flags, lector: true })
      : json(session));

    await expect(getReviewSession("course-1", 5)).resolves.toEqual(session);
    expect(mockFetch).toHaveBeenLastCalledWith(
      expect.stringContaining("/progress/courses/course-1/review-session?max_items=5"),
      expect.anything(),
    );
  });
});

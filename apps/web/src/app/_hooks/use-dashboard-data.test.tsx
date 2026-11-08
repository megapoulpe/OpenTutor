import { cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useCourseStore } from "@/store/course";
import { useDashboardData } from "./use-dashboard-data";

const { replace, fetchCourses } = vi.hoisted(() => ({
  replace: vi.fn(), fetchCourses: vi.fn(async () => {}),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));
vi.mock("@/lib/i18n-context", () => ({ useT: () => t, useTF: () => t }));
const t = (key: string) => key;
vi.mock("@/lib/study-notifications", () => ({ initStudyNotifications: () => () => {} }));
vi.mock("@/lib/api", () => ({
  getHealthStatus: vi.fn(async () => ({})),
  getReviewSession: vi.fn(async () => ({ items: [] })),
  listNotifications: vi.fn(async () => ({ notifications: [] })),
  listAgentTasks: vi.fn(async () => []),
  listStudyGoals: vi.fn(async () => []),
  getWeeklyReport: vi.fn(async () => null),
  getLearningOverview: vi.fn(async () => null),
  getCourseProgress: vi.fn(async () => null),
  getKnowledgeGraph: vi.fn(async () => ({ nodes: [] })),
  approveAgentTask: vi.fn(), rejectAgentTask: vi.fn(), logAgentDecision: vi.fn(),
  markTaskNotificationsRead: vi.fn(),
}));

describe("dashboard navigation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    useCourseStore.setState({ courses: [], loading: false, error: null, fetchCourses });
  });
  afterEach(cleanup);

  it("keeps the management page accessible with a single course, including on return", async () => {
    useCourseStore.setState({ courses: [{
      id: "course-1", name: "My course", description: null,
      created_at: "2026-11-08T00:00:00Z", updated_at: null,
      file_count: 0, content_node_count: 0, active_goal_count: 0,
      pending_task_count: 0, pending_approval_count: 0,
      last_agent_activity_at: null, last_scene_id: null,
    }] });
    const first = renderHook(() => useDashboardData());
    await waitFor(() => expect(localStorage.getItem("opentutor_onboarded")).toBe("true"));
    expect(replace).not.toHaveBeenCalled();
    first.unmount();

    renderHook(() => useDashboardData());
    await waitFor(() => expect(fetchCourses).toHaveBeenCalledTimes(2));
    expect(replace).not.toHaveBeenCalled();
  });

  it("still sends a new account without courses to setup", async () => {
    renderHook(() => useDashboardData());
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/setup"));
  });
});

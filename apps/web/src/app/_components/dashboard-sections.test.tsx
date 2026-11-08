import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { LocaleProvider } from "@/lib/i18n-context";
import { setLocale } from "@/lib/i18n";
import type { LearningOverview, WeeklyReport } from "@/lib/api";
import { MasteryOverviewSection, WeeklyStatsSection } from "./dashboard-sections";

const weeklyReport: WeeklyReport = {
  period: { start: "2026-11-02", end: "2026-11-08" },
  this_week: { study_minutes: 30, active_days: 2, quiz_total: 4, quiz_correct: 3, accuracy: 75 },
  last_week: { study_minutes: 10, active_days: 1, quiz_total: 2, quiz_correct: 1, accuracy: 50 },
  deltas: { study_minutes: 20, accuracy: 25, quiz_total: 2 },
  mastery_avg: 0.5, highlights: ["Completed 4 quiz questions"],
};
const masteryOverview: LearningOverview = {
  total_courses: 1, total_study_minutes: 30, average_mastery: 0.5,
  gap_type_breakdown: {}, diagnosis_breakdown: {}, error_category_breakdown: {},
  course_summaries: [{ course_id: "course-1", course_name: "Algebra", average_mastery: 0.5,
    study_minutes: 30, wrong_answers: 1, diagnosed_count: 0, gap_types: {} }],
};

describe("dashboard statistics language", () => {
  beforeEach(() => { localStorage.clear(); setLocale("en"); });
  afterEach(cleanup);

  it("renders weekly labels, units and comparisons in English", () => {
    const { container } = render(<LocaleProvider><WeeklyStatsSection weeklyReport={weeklyReport} /></LocaleProvider>);
    expect(screen.getByText("This Week's Learning Stats")).toBeInTheDocument();
    expect(screen.getByText("Study Time")).toBeInTheDocument();
    expect(screen.getByText("Quiz Accuracy")).toBeInTheDocument();
    expect(screen.getByText("Active Days")).toBeInTheDocument();
    expect(screen.getByText("Last week: 10 min")).toBeInTheDocument();
    expect(screen.getByText("Last week: 50%")).toBeInTheDocument();
    expect(screen.getByText("Last week: 1 d")).toBeInTheDocument();
    expect(screen.getByText("Completed 4 quiz questions")).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/[\u3400-\u9fff]/);
  });

  it("renders mastery labels and units in English", () => {
    const { container } = render(<LocaleProvider><MasteryOverviewSection masteryOverview={masteryOverview} onNavigate={() => {}} /></LocaleProvider>);
    expect(screen.getByText("Cross-Course Mastery")).toBeInTheDocument();
    expect(screen.getByText("Average Mastery")).toBeInTheDocument();
    expect(screen.getByText("Total Study Time")).toBeInTheDocument();
    expect(screen.getByText("Algebra")).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/[\u3400-\u9fff]/);
  });

  it("keeps Chinese translations available when Chinese is selected", () => {
    setLocale("zh");
    render(<LocaleProvider><WeeklyStatsSection weeklyReport={weeklyReport} /></LocaleProvider>);
    expect(screen.getByText("本周学习统计")).toBeInTheDocument();
    expect(screen.getByText("上周 10 分钟")).toBeInTheDocument();
    expect(screen.queryByText("Study Time")).not.toBeInTheDocument();
  });
});

import type { RestaurantResult } from "@/types";

type ResultInput = Partial<RestaurantResult> & Pick<RestaurantResult, "name">;

export type ResultView = {
  /** Group satisfaction, 0-100. Null when the server did not send it. */
  percent: number | null;
  /** "3/3 positive" */
  positiveLine: string | null;
  /** "2 Likes · 1 Super Like · 0 Passes" */
  breakdown: string | null;
  badge: string | null;
  /** Why it could not win, without saying who caused it. */
  eligibility: string | null;
};

export const SATISFACTION_LABEL = "Group satisfaction";
export const SATISFACTION_HINT = "Share of the group who chose Like or Super Like.";

const NOT_ELIGIBLE: Record<string, string> = {
  veto: "Removed by a group veto",
  budget: "Above the group's budget",
  distance: "Outside the group's distance limit",
  diet: "Misses a dietary requirement",
};

/** Renders only aggregate numbers the server sent. Never recomputes the ranking. */
export function describeResult(result: ResultInput): ResultView {
  const percent = isCount(result.satisfaction_percent) ? clamp(result.satisfaction_percent) : null;
  const { likes, super_likes: superLikes, passes, total_participants: total } = result;

  let positiveLine: string | null = null;
  let breakdown: string | null = null;
  if (isCount(likes) && isCount(superLikes) && isCount(total) && total > 0) {
    const positives = isCount(result.positives) ? result.positives : likes + superLikes;
    positiveLine = `${positives}/${total} positive`;
    const parts = [count(likes, "Like"), count(superLikes, "Super Like")];
    if (isCount(passes)) parts.push(count(passes, "Pass", "Passes"));
    breakdown = parts.join(" · ");
  }

  let badge: string | null = null;
  if (result.highlight === "best_balance") badge = "Best overall balance";
  if (result.highlight === "strongest_support") badge = "Strongest overall support";
  if (result.highlight === "higher_satisfaction") badge = "Higher satisfaction";

  const eligibility = result.eliminated
    ? `Not eligible · ${NOT_ELIGIBLE[result.elimination_reason ?? ""] ?? "Removed by a group limit"}`
    : null;

  return { percent, positiveLine, breakdown, badge, eligibility };
}

export function whyThisWon(result: ResultInput): string {
  const text = result.explanation?.trim();
  return text || "Nomly picked this as the best balance for the whole group.";
}

function isCount(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

function clamp(value: number) {
  return Math.min(100, Math.max(0, Math.round(value)));
}

function count(value: number, one: string, many = `${one}s`) {
  return `${value} ${value === 1 ? one : many}`;
}

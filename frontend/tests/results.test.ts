import assert from "node:assert/strict";
import { test } from "node:test";

const { describeResult, whyThisWon, SATISFACTION_HINT, SATISFACTION_LABEL } = await import("../lib/results.ts");

const winner = {
  restaurant_id: "keen",
  name: "Keen Taqueria",
  likes: 0,
  super_likes: 2,
  passes: 2,
  vetoes: 0,
  positives: 2,
  total_participants: 4,
  satisfaction_percent: 50,
  compatibility_percent: 50,
  eliminated: false,
  elimination_reason: null,
  highlight: "strongest_support" as const,
  explanation:
    "Wide Bistro had higher group satisfaction (75% vs 50%), but Keen Taqueria had stronger overall support. Nomly counts a Super Like as a stronger vote than a Like, and Keen Taqueria got 2 Super Likes. 2 of 4 were positive (0 Likes, 2 Super Likes, 2 Passes). Nobody vetoed it.",
};

const higherAlternative = {
  restaurant_id: "wide",
  name: "Wide Bistro",
  likes: 3,
  super_likes: 0,
  passes: 1,
  vetoes: 0,
  positives: 3,
  total_participants: 4,
  satisfaction_percent: 75,
  compatibility_percent: 75,
  eliminated: false,
  highlight: "higher_satisfaction" as const,
  explanation: "3 of 4 were positive (3 Likes, 0 Super Likes, 1 Pass).",
};

test("a 50% winner and a 75% alternative both show their real group satisfaction", () => {
  const top = describeResult(winner);
  const other = describeResult(higherAlternative);
  assert.equal(top.percent, 50);
  assert.equal(other.percent, 75);
  assert.equal(top.badge, "Strongest overall support");
  assert.equal(other.badge, "Higher satisfaction");
  assert.equal(other.eligibility, null);
});

test("why this won is separate from group satisfaction and names the deciding factor", () => {
  const why = whyThisWon(winner);
  assert.match(why, /higher group satisfaction \(75% vs 50%\)/);
  assert.match(why, /stronger overall support/);
  assert.doesNotMatch(why, /highest group satisfaction/);
  assert.notEqual(SATISFACTION_LABEL, "Why this won");
});

test("best_balance still maps to its badge", () => {
  assert.equal(describeResult({ name: "A", highlight: "best_balance" }).badge, "Best overall balance");
});

for (const [likes, superLikes, passes, percent] of [
  [3, 0, 0, 100],
  [2, 1, 0, 100],
  [2, 0, 1, 67],
  [1, 0, 2, 33],
  [0, 3, 0, 100],
] as const) {
  test(`${likes} Likes, ${superLikes} Super Likes, ${passes} Passes shows ${percent}%`, () => {
    const view = describeResult({
      name: "A",
      likes,
      super_likes: superLikes,
      passes,
      positives: likes + superLikes,
      total_participants: 3,
      satisfaction_percent: percent,
    });
    assert.equal(view.percent, percent);
    assert.equal(view.positiveLine, `${likes + superLikes}/3 positive`);
  });
}

test("3/3 positive is shown as 100% group satisfaction", () => {
  const view = describeResult({ name: "DooBoo", likes: 2, super_likes: 1, passes: 0, positives: 3, total_participants: 3, satisfaction_percent: 100 });
  assert.equal(view.percent, 100);
  assert.equal(view.positiveLine, "3/3 positive");
  assert.equal(view.breakdown, "2 Likes · 1 Super Like · 0 Passes");
  assert.match(SATISFACTION_HINT, /Like or Super Like/);
});

test("pass counts and singular wording", () => {
  const view = describeResult({ name: "A", likes: 1, super_likes: 0, passes: 2, positives: 1, total_participants: 3 });
  assert.equal(view.positiveLine, "1/3 positive");
  assert.equal(view.breakdown, "1 Like · 0 Super Likes · 2 Passes");
});

test("positives fall back to likes plus super likes", () => {
  const view = describeResult({ name: "A", likes: 0, super_likes: 1, passes: 2, total_participants: 3 });
  assert.equal(view.positiveLine, "1/3 positive");
});

test("percentages render as whole numbers inside 0-100", () => {
  assert.equal(describeResult({ name: "A", satisfaction_percent: 66.6 }).percent, 67);
  assert.equal(describeResult({ name: "A", satisfaction_percent: 140 }).percent, 100);
});

test("missing metrics hide the numbers instead of guessing", () => {
  const view = describeResult({ name: "Old Server Result", compatibility_percent: 80 });
  assert.equal(view.percent, null);
  assert.equal(view.positiveLine, null);
  assert.equal(view.breakdown, null);
  assert.equal(view.badge, null);
});

test("missing explanation falls back to neutral copy", () => {
  assert.equal(whyThisWon({ name: "A", explanation: "  " }), "Nomly picked this as the best balance for the whole group.");
  assert.equal(whyThisWon({ name: "A" }), "Nomly picked this as the best balance for the whole group.");
});

test("vetoed alternatives are marked not eligible without saying who", () => {
  const view = describeResult({ name: "Fav", eliminated: true, elimination_reason: "veto", satisfaction_percent: 67 });
  assert.equal(view.eligibility, "Not eligible · Removed by a group veto");
  assert.equal(view.percent, 67);
});

test("budget, distance, diet, and unknown limits have their own wording", () => {
  assert.match(describeResult({ name: "A", eliminated: true, elimination_reason: "budget" }).eligibility ?? "", /budget/);
  assert.match(describeResult({ name: "A", eliminated: true, elimination_reason: "distance" }).eligibility ?? "", /distance/);
  assert.match(describeResult({ name: "A", eliminated: true, elimination_reason: "diet" }).eligibility ?? "", /dietary/);
  assert.equal(describeResult({ name: "A", eliminated: true }).eligibility, "Not eligible · Removed by a group limit");
});

test("a normal winner has no badge and no eligibility note", () => {
  const view = describeResult({ ...winner, highlight: null });
  assert.equal(view.badge, null);
  assert.equal(view.eligibility, null);
});

test("rendered text contains only aggregate numbers, never names", () => {
  const view = describeResult(winner);
  const rendered = [view.positiveLine, view.breakdown, view.badge, view.eligibility, whyThisWon(winner)].join(" ");
  for (const name of ["Abdalla", "Sarah", "Omar"]) assert.doesNotMatch(rendered, new RegExp(name));
});

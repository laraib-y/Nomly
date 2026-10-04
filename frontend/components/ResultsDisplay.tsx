"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

import { ContactDetails, FoodPhoto, RatingPrice } from "@/components/RestaurantInfo";
import { NOT_AVAILABLE, cuisineWash, formatCuisine } from "@/lib/format";
import { SATISFACTION_HINT, SATISFACTION_LABEL, describeResult, whyThisWon } from "@/lib/results";
import type { Results } from "@/types";

/** Winner card and other options. Shared by the live results screen and dinner history. */
export function ResultsDisplay({
  results,
  eyebrow = "Your group's pick",
  whyActions,
}: {
  results: Results;
  eyebrow?: string;
  whyActions?: ReactNode;
}) {
  const top = results.top_match;
  if (!top) return null;
  const alternatives = results.alternatives || [];
  const others = alternatives.filter((item, index) => index < 4 || item.highlight === "higher_satisfaction");
  const view = describeResult(top);
  const why = whyThisWon(top);

  return (
    <>
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <p className="text-sm uppercase tracking-[0.22em] text-chili">{eyebrow}</p>
        <article className="mt-4 overflow-hidden rounded-[32px] border border-line bg-card shadow-card">
          <FoodPhoto restaurant={top} className="aspect-[16/9] w-full" />
          <div className="px-6 py-8 sm:px-10" style={{ background: cuisineWash(top.cuisine) }}>
            <p className="text-xs uppercase tracking-[0.18em]">{formatCuisine(top.cuisine) ?? `Cuisine · ${NOT_AVAILABLE}`}</p>
            <h1 className="mt-3 break-words font-serif text-5xl leading-none sm:text-6xl">{top.name}</h1>
          </div>
          <div className="space-y-4 px-6 py-8 sm:px-10">
            {view.badge ? (
              <span className="inline-block rounded-full bg-paper px-3 py-1 text-xs uppercase tracking-[0.14em] text-moss">
                {view.badge}
              </span>
            ) : null}
            {view.percent !== null ? (
              <div>
                <p className="text-lg" title={SATISFACTION_HINT}>
                  {SATISFACTION_LABEL}
                </p>
                <p className="font-serif text-5xl text-moss">{view.percent}%</p>
                <SatisfactionBar percent={view.percent} />
              </div>
            ) : null}
            {view.positiveLine ? (
              <p className="text-ink-soft">
                <span className="text-ink">{view.positiveLine}</span>
                {view.breakdown ? ` · ${view.breakdown}` : ""}
              </p>
            ) : null}
            {view.eligibility ? <p className="text-sm text-chili">{view.eligibility}</p> : null}
            <div className="space-y-3 border-t border-line pt-4">
              <RatingPrice restaurant={top} />
              <ContactDetails restaurant={top} />
            </div>
            <div className="border-t border-line pt-4">
              <h2 className="font-serif text-2xl">Why this won</h2>
              <p className="mt-2 text-ink-soft">{why}</p>
            </div>
            {whyActions}
          </div>
        </article>
      </motion.div>

      {others.length > 0 ? (
        <div className="mt-8">
          <h2 className="font-serif text-3xl">Other options</h2>
          <p className="mt-1 text-sm text-ink-soft">
            Percentages are {SATISFACTION_LABEL.toLowerCase()}. Nomly ranks by fairness first, so the highest number
            does not always win.
          </p>
          <ul className="mt-4 space-y-3">
            {others.map((restaurant) => {
              const item = describeResult(restaurant);
              return (
                <li
                  key={restaurant.restaurant_id}
                  className={`rounded-2xl border border-line bg-card px-4 py-4 ${item.eligibility ? "opacity-70" : ""}`}
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex min-w-0 items-center gap-3">
                      <FoodPhoto restaurant={restaurant} compact className="h-14 w-14 shrink-0 rounded-xl" />
                      <div className="min-w-0">
                        <p className="truncate font-medium" title={restaurant.name}>
                          {restaurant.name}
                        </p>
                        <p className="text-sm text-ink-soft">
                          {formatCuisine(restaurant.cuisine) ?? `Cuisine · ${NOT_AVAILABLE}`}
                        </p>
                      </div>
                    </div>
                    {item.percent !== null ? (
                      <div className="text-right">
                        <p className="font-serif text-2xl">{item.percent}%</p>
                        <p className="text-xs text-ink-soft">satisfaction</p>
                      </div>
                    ) : null}
                  </div>
                  {item.percent !== null ? <SatisfactionBar percent={item.percent} muted={Boolean(item.eligibility)} /> : null}
                  <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-soft">
                    {item.positiveLine ? (
                      <span>
                        {item.positiveLine}
                        {item.breakdown ? ` · ${item.breakdown}` : ""}
                      </span>
                    ) : null}
                    {item.badge ? (
                      <span className="rounded-full bg-paper px-2 py-0.5 text-xs uppercase tracking-[0.12em] text-gold">
                        {item.badge}
                      </span>
                    ) : null}
                    {item.eligibility ? <span className="text-chili">{item.eligibility}</span> : null}
                  </div>
                  <details className="mt-3 text-sm">
                    <summary className="cursor-pointer text-ink-soft underline underline-offset-4">
                      Restaurant details<span className="sr-only"> for {restaurant.name}</span>
                    </summary>
                    <div className="mt-3 space-y-3">
                      <RatingPrice restaurant={restaurant} />
                      <ContactDetails restaurant={restaurant} />
                    </div>
                  </details>
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}
    </>
  );
}

export function SatisfactionBar({ percent, muted = false }: { percent: number; muted?: boolean }) {
  return (
    <div
      className="mt-3 h-2 rounded-full bg-paper-deep"
      role="progressbar"
      aria-label={SATISFACTION_LABEL}
      aria-valuenow={percent}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className={`h-2 rounded-full ${muted ? "bg-ink-soft" : "bg-moss"}`} style={{ width: `${percent}%` }} />
    </div>
  );
}

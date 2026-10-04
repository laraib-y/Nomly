"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { useState } from "react";

import { TIMELINE_BOX, describeHistoryItem, percentToY, timelinePath, timelinePoints, timelineTicks } from "@/lib/history";
import type { HistoryItem } from "@/types";

const STRONG = 67;

function dotColor(percent: number) {
  if (percent >= STRONG) return "bg-moss";
  if (percent >= 34) return "bg-gold";
  return "bg-chili";
}

/** Each finished dinner is a plate on a line: when it happened, and how much of the table liked the winner. */
export function SatisfactionTimeline({ items }: { items: HistoryItem[] }) {
  const reduceMotion = useReducedMotion();
  const points = timelinePoints(items);
  const [active, setActive] = useState<string | null>(points.length ? points[points.length - 1].item.session_id : null);
  if (!points.length) return null;

  const box = TIMELINE_BOX;
  const path = timelinePath(points);
  const ticks = timelineTicks(points);
  const selected = points.find((point) => point.item.session_id === active) ?? null;
  const strongTop = percentToY(100);
  const strongBottom = percentToY(STRONG);
  const left = (x: number) => `${(x / box.width) * 100}%`;
  const top = (y: number) => `${(y / box.height) * 100}%`;

  return (
    <figure className="m-0">
      <figcaption className="sr-only">
        Group satisfaction for {points.length} {points.length === 1 ? "dinner" : "dinners"}, oldest to newest.
      </figcaption>
      <div className="relative ml-10 h-56 sm:h-64" data-testid="satisfaction-timeline">
        {[100, 50, 0].map((percent) => (
          <span
            key={percent}
            className="absolute -left-10 w-8 -translate-y-1/2 text-right text-xs text-ink-soft"
            style={{ top: top(percentToY(percent)) }}
          >
            {percent}%
          </span>
        ))}
        <svg
          viewBox={`0 0 ${box.width} ${box.height}`}
          preserveAspectRatio="none"
          className="absolute inset-0 h-full w-full overflow-visible"
          aria-hidden="true"
        >
          <rect
            x={0}
            y={strongTop}
            width={box.width}
            height={strongBottom - strongTop}
            className="fill-croc/20"
            rx={6}
          />
          {[100, 75, 50, 25, 0].map((percent) => (
            <line
              key={percent}
              x1={0}
              x2={box.width}
              y1={percentToY(percent)}
              y2={percentToY(percent)}
              className="stroke-line"
              strokeWidth={percent % 50 === 0 ? 1.5 : 1}
              strokeDasharray={percent % 50 === 0 ? undefined : "3 6"}
              vectorEffect="non-scaling-stroke"
            />
          ))}
          {path ? (
            <>
              <path d={path} fill="none" className="stroke-croc" strokeWidth={7} strokeLinecap="round" vectorEffect="non-scaling-stroke" opacity={0.45} />
              <motion.path
                d={path}
                fill="none"
                className="stroke-ink"
                strokeWidth={1.75}
                strokeLinecap="round"
                vectorEffect="non-scaling-stroke"
                initial={reduceMotion ? false : { pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 1.1, ease: "easeInOut" }}
              />
            </>
          ) : null}
        </svg>
        <span className="pointer-events-none absolute right-2 text-[11px] uppercase tracking-[0.16em] text-moss/70" style={{ top: top(strongTop + 4) }}>
          Strong match
        </span>

        {points.map((point, index) => {
          const isActive = point.item.session_id === active;
          // Centering lives on the wrapper: framer-motion owns the button's transform for the pop-in.
          return (
            <div
              key={point.item.session_id}
              className="absolute z-10 -translate-x-1/2 -translate-y-1/2"
              style={{ left: left(point.x), top: top(point.y) }}
            >
              <motion.button
                type="button"
                aria-label={`${point.item.winner?.name ?? "Dinner"}, ${point.percent}% group satisfaction`}
                aria-pressed={isActive}
                onClick={() => setActive(point.item.session_id)}
                onMouseEnter={() => setActive(point.item.session_id)}
                onFocus={() => setActive(point.item.session_id)}
                initial={reduceMotion ? false : { scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: reduceMotion ? 0 : 0.25 + index * 0.06, type: "spring", stiffness: 380, damping: 18 }}
                className="flex h-9 w-9 items-center justify-center rounded-full"
              >
                <span
                  className={`block rounded-full border-[3px] border-card shadow ${dotColor(point.percent)} ${
                    isActive ? "h-5 w-5 ring-2 ring-ink/70" : "h-3.5 w-3.5"
                  }`}
                />
              </motion.button>
            </div>
          );
        })}

        {selected ? <Tooltip point={selected} left={left(selected.x)} top={top(selected.y)} /> : null}
      </div>
      <div className="relative ml-10 mt-2 h-5 text-xs text-ink-soft" aria-hidden="true">
        {ticks.map((tick, index) => (
          <span
            key={tick.label}
            className={`absolute whitespace-nowrap ${
              index === 0 && ticks.length > 1 ? "" : index === ticks.length - 1 && ticks.length > 1 ? "-translate-x-full" : "-translate-x-1/2"
            }`}
            style={{ left: left(tick.x) }}
          >
            {tick.label}
          </span>
        ))}
      </div>
    </figure>
  );
}

function Tooltip({ point, left, top }: { point: ReturnType<typeof timelinePoints>[number]; left: string; top: string }) {
  const text = describeHistoryItem(point.item);
  const flipDown = point.percent >= 50;
  const alignRight = point.x > TIMELINE_BOX.width * 0.66;
  const alignLeft = point.x < TIMELINE_BOX.width * 0.34;
  return (
    <div
      role="status"
      className={`pointer-events-auto absolute z-20 w-52 rounded-2xl border border-line bg-card p-3 text-sm shadow-card ${
        alignRight ? "-translate-x-[90%]" : alignLeft ? "-translate-x-[10%]" : "-translate-x-1/2"
      } ${flipDown ? "mt-6" : "-mt-6 -translate-y-full"}`}
      style={{ left, top }}
    >
      <p className="truncate font-serif text-lg leading-tight">
        <span aria-hidden="true">{text.emoji}</span> {text.title}
      </p>
      <p className="mt-1 text-moss">{point.percent}% satisfaction</p>
      <p className="text-ink-soft">{text.meta}</p>
      <p className="truncate text-ink-soft">{text.subtitle}</p>
      <Link href={`/history/${point.item.session_id}`} className="mt-2 inline-block underline underline-offset-4">
        Open dinner →
      </Link>
    </div>
  );
}

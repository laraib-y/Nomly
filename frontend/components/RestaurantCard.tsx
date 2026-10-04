"use client";

import { motion } from "framer-motion";

import { cuisineWash, formatPrice, formatRating } from "@/lib/format";
import type { Restaurant } from "@/types";

export function RestaurantCard({ restaurant }: { restaurant: Restaurant }) {
  const price = formatPrice(restaurant.price);
  const rating = formatRating(restaurant.rating);
  const meta = [restaurant.cuisine, price].filter(Boolean).join(" · ");

  return (
    <article className="overflow-hidden rounded-[28px] border border-line bg-card shadow-card">
      <div className="relative h-48" style={{ background: cuisineWash(restaurant.cuisine) }}>
        {restaurant.image_url ? (
          // External place photos are optional and may fail. The wash remains underneath.
          <img
            src={restaurant.image_url}
            alt=""
            className="h-full w-full object-cover"
            onError={(event) => {
              event.currentTarget.style.display = "none";
            }}
          />
        ) : (
          <div className="flex h-full items-end p-6">
            <p className="font-serif text-4xl">{restaurant.cuisine || "Dinner"}</p>
          </div>
        )}
      </div>
      <div className="space-y-3 p-6">
        <h2 className="font-serif text-4xl leading-none">{restaurant.name}</h2>
        {meta ? <p className="text-sm text-ink-soft">{meta}</p> : null}
        {rating ? <p className="text-sm">{rating}</p> : null}
        {restaurant.address ? <p className="text-sm">{restaurant.address}</p> : null}
        {restaurant.description ? <p className="text-sm leading-relaxed text-ink-soft">{restaurant.description}</p> : null}
      </div>
    </article>
  );
}

export function DecisionButtons({
  disabled,
  onPass,
  onLike,
}: {
  disabled: boolean;
  onPass: () => void;
  onLike: () => void;
}) {
  return (
    <div className="mt-5 grid grid-cols-2 gap-3">
      <button
        type="button"
        disabled={disabled}
        onClick={onPass}
        className="rounded-full border border-ink/15 bg-card px-5 py-3 disabled:opacity-50"
      >
        Pass
      </button>
      <motion.button
        type="button"
        disabled={disabled}
        onClick={onLike}
        whileTap={{ scale: 0.98 }}
        className="rounded-full bg-moss px-5 py-3 text-white disabled:opacity-50"
      >
        Like
      </motion.button>
    </div>
  );
}

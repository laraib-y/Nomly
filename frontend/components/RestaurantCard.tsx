"use client";

import { useState } from "react";

import { cuisineWash, formatPrice } from "@/lib/format";
import type { Restaurant } from "@/types";

export function RestaurantCard({ restaurant }: { restaurant: Restaurant }) {
  const [imageFailed, setImageFailed] = useState(false);
  const showImage = Boolean(restaurant.image_url) && !imageFailed;
  const price = formatPrice(restaurant.price);
  const rating = restaurant.rating != null ? restaurant.rating.toFixed(1) : null;
  const chip = "rounded-full border border-ink/15 px-3 py-0.5 text-ink-soft";

  return (
    <article className="flex aspect-square w-full flex-col overflow-hidden rounded-3xl border border-ink/10 bg-card shadow-[0_8px_24px_-12px_rgba(36,28,24,0.18)]">
      <div
        className="relative min-h-0 flex-1 border-b-[3px] border-ink"
        style={{ background: cuisineWash(restaurant.cuisine) }}
      >
        {showImage ? (
          // External place photos are optional and may fail. The colored wash stays underneath.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={restaurant.image_url as string}
            alt=""
            className="absolute inset-0 h-full w-full object-cover"
            onError={() => setImageFailed(true)}
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/assets/IMG_8293.webp" alt="" className="h-[85%] w-auto object-contain" />
          </div>
        )}
      </div>

      <div className="px-5 pb-4 pt-3">
        <h2 className="line-clamp-2 text-3xl leading-tight">{restaurant.name}</h2>
        <div className="mt-2 flex flex-wrap gap-2 text-sm">
          {restaurant.cuisine ? <span className={`${chip} bg-croc`}>{restaurant.cuisine}</span> : null}
          {price ? <span className={`${chip} bg-paper-deep`}>{price}</span> : null}
          {rating ? <span className={`${chip} bg-card`}>★ {rating}</span> : null}
        </div>
        {restaurant.description ? (
          <p className="mt-2 line-clamp-2 text-sm leading-snug text-ink-soft">{restaurant.description}</p>
        ) : restaurant.address ? (
          <p className="mt-2 truncate text-sm text-ink-soft">{restaurant.address}</p>
        ) : null}
      </div>
    </article>
  );
}

function ImageButton({
  src,
  label,
  onClick,
  disabled,
}: {
  src: string;
  label: string;
  onClick: () => void;
  disabled: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      style={{ backgroundImage: `url(${src})`, backgroundSize: "100% 100%" }}
      className="relative block aspect-[632/238] w-full select-none bg-no-repeat transition-transform duration-75 enabled:hover:-translate-y-0.5 enabled:active:translate-y-0.5 enabled:active:scale-[0.98] disabled:opacity-50"
    >
      <span className="absolute inset-x-0 bottom-0 flex h-[74%] items-center justify-center text-xl text-ink">
        {label}
      </span>
    </button>
  );
}

export function DecisionButtons({
  disabled,
  superLikeLeft,
  vetoLeft,
  onPass,
  onLike,
  onSuperLike,
  onVeto,
}: {
  disabled: boolean;
  superLikeLeft: boolean;
  vetoLeft: boolean;
  onPass: () => void;
  onLike: () => void;
  onSuperLike: () => void;
  onVeto: () => void;
}) {
  const extra = "text-sm text-ink-soft underline underline-offset-4 disabled:no-underline disabled:opacity-40";

  return (
    <div className="mt-5">
      <div className="grid grid-cols-2 gap-5">
        <ImageButton src="/assets/btn-pass.webp" label="Pass" onClick={onPass} disabled={disabled} />
        <ImageButton src="/assets/btn-snack.webp" label="Snack" onClick={onLike} disabled={disabled} />
      </div>
      <div className="mt-5 flex justify-center gap-6">
        <button type="button" disabled={disabled || !superLikeLeft} onClick={onSuperLike} className={extra}>
          {superLikeLeft ? "Super snack · 1 left" : "Super snack used"}
        </button>
        <button type="button" disabled={disabled || !vetoLeft} onClick={onVeto} className={extra}>
          {vetoLeft ? "Veto · 1 left" : "Veto used"}
        </button>
      </div>
    </div>
  );
}
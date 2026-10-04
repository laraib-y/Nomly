"use client";

import { ContactDetails, FoodPhoto, RatingPrice } from "@/components/RestaurantInfo";
import { NOT_AVAILABLE, formatCuisine } from "@/lib/format";
import type { Restaurant } from "@/types";

export function RestaurantCard({ restaurant }: { restaurant: Restaurant }) {
  const cuisine = formatCuisine(restaurant.cuisine, restaurant.categories);

  return (
    <article className="flex w-full flex-col overflow-hidden rounded-3xl bg-[#fffaf3] shadow-[0_10px_30px_-14px_rgba(36,28,24,0.28)]">
      <FoodPhoto restaurant={restaurant} className="aspect-[2/1] w-full border-b-[3px] border-ink" />

      <div className="space-y-3 px-5 pb-5 pt-3">
        <div className="min-w-0">
          <h2 className="line-clamp-2 break-words text-2xl leading-tight sm:text-3xl" title={restaurant.name}>
            {restaurant.name}
          </h2>
          <p className="mt-1 text-sm text-ink-soft">
            {cuisine ?? (
              <>
                <span className="text-ink">Cuisine</span> · {NOT_AVAILABLE}
              </>
            )}
          </p>
        </div>
        <RatingPrice restaurant={restaurant} />
        <ContactDetails restaurant={restaurant} />
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
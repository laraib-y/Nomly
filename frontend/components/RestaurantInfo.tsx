"use client";

import { useState, type PointerEvent, type ReactNode } from "react";

import { getCuisineImage, getRestaurantImage, type ImageInput } from "@/lib/foodImages";
import { NOT_AVAILABLE, describeRestaurant, type RestaurantInfoInput } from "@/lib/format";

type Restaurantish = RestaurantInfoInput & ImageInput;

/** Food photo with an honest label when it only represents the cuisine. */
export function FoodPhoto({
  restaurant,
  className = "",
  compact = false,
}: {
  restaurant: Restaurantish;
  className?: string;
  /** Thumbnails keep the honesty note as a tooltip instead of a label. */
  compact?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  const image = failed ? getCuisineImage(restaurant) : getRestaurantImage(restaurant);

  return (
    <div
      className={`relative overflow-hidden bg-paper-deep ${className}`}
      title={compact && image.representative ? "Representative photo" : undefined}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={image.src}
        alt={image.alt}
        draggable={false}
        className="absolute inset-0 h-full w-full select-none object-cover"
        onError={() => {
          if (image.source === "provider") setFailed(true);
        }}
      />
      {image.representative && !compact ? (
        <span className="absolute bottom-2 right-2 rounded-full bg-ink/70 px-2 py-0.5 text-[11px] text-paper">
          Representative photo
        </span>
      ) : null}
    </div>
  );
}

/** Rating and price chips with explicit fallbacks. */
export function RatingPrice({ restaurant }: { restaurant: Restaurantish }) {
  const info = describeRestaurant(restaurant);
  const chip = "rounded-full border border-line bg-paper px-3 py-0.5";
  return (
    <div className="flex flex-wrap gap-2 text-sm">
      <span className={chip}>
        {info.rating ? (
          <>
            <span aria-hidden="true">⭐</span> {info.rating}
            <span className="sr-only"> out of 5</span>
          </>
        ) : (
          <>Rating · {NOT_AVAILABLE}</>
        )}
      </span>
      <span className={chip}>
        {info.price ? (
          <>
            {info.price}
            <span className="sr-only"> price range</span>
          </>
        ) : (
          <>Price range · {NOT_AVAILABLE}</>
        )}
      </span>
    </div>
  );
}

/** Location, phone and website. Missing values say so instead of rendering empty or invented data. */
export function ContactDetails({ restaurant }: { restaurant: Restaurantish }) {
  const info = describeRestaurant(restaurant);
  const link = "underline decoration-line underline-offset-4 hover:text-chili";
  const stop = { onPointerDownCapture: (event: PointerEvent) => event.stopPropagation() };

  return (
    <dl className="space-y-1.5 text-sm">
      <Row icon="📍" label="Location">
        {info.address ? (
          <>
            <span className="break-words">{info.address}</span>
            {info.map ? (
              <>
                {" "}
                <a
                  href={info.map}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`View ${restaurant.name} location on map`}
                  className={`${link} whitespace-nowrap`}
                  {...stop}
                >
                  View on map →
                </a>
              </>
            ) : null}
          </>
        ) : (
          <Missing label="Location" />
        )}
      </Row>
      <Row icon="☎" label="Phone number">
        {info.phone ? (
          <a href={info.phone.href} aria-label={`Call ${restaurant.name}`} className={link} {...stop}>
            {info.phone.display}
          </a>
        ) : (
          <Missing label="Phone number" />
        )}
      </Row>
      <Row icon="🌐" label="Website">
        {info.website ? (
          <a
            href={info.website.href}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`Visit ${restaurant.name} restaurant website`}
            className={`${link} break-all`}
            {...stop}
          >
            Visit restaurant →
          </a>
        ) : (
          <Missing label="Website" />
        )}
      </Row>
    </dl>
  );
}

function Row({ icon, label, children }: { icon: string; label: string; children: ReactNode }) {
  return (
    <div className="flex min-w-0 gap-2">
      <span aria-hidden="true" className="w-5 shrink-0 text-center">
        {icon}
      </span>
      <div className="min-w-0">
        <dt className="sr-only">{label}</dt>
        <dd className="min-w-0 text-ink-soft">{children}</dd>
      </div>
    </div>
  );
}

function Missing({ label }: { label: string }) {
  return (
    <span>
      <span className="text-ink">{label}</span> · {NOT_AVAILABLE}
    </span>
  );
}

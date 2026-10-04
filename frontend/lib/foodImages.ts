import { safeExternalUrl } from "./format.ts";

export type FoodImage = {
  src: string;
  alt: string;
  /** True when the picture shows the cuisine, not this restaurant. */
  representative: boolean;
  source: "provider" | "cuisine" | "generic";
};

type CuisinePhoto = { src: string; alt: string };

const GENERIC: CuisinePhoto = { src: "/food/generic.webp", alt: "Shared dinner dishes" };

const PHOTOS: Record<string, CuisinePhoto[]> = {
  korean: [
    { src: "/food/korean-1.webp", alt: "Korean BBQ with banchan" },
    { src: "/food/korean-2.webp", alt: "Korean bibimbap in a stone bowl" },
  ],
  japanese: [
    { src: "/food/japanese-1.webp", alt: "Japanese sushi platter" },
    { src: "/food/japanese-2.webp", alt: "Japanese tonkotsu ramen" },
  ],
  chinese: [{ src: "/food/chinese.webp", alt: "Chinese soup dumplings and chili noodles" }],
  indian: [{ src: "/food/indian.webp", alt: "Indian butter chicken, biryani and naan" }],
  mexican: [{ src: "/food/mexican.webp", alt: "Mexican tacos al pastor" }],
  italian: [{ src: "/food/italian.webp", alt: "Italian pasta and margherita pizza" }],
  thai: [{ src: "/food/thai.webp", alt: "Thai pad thai with shrimp" }],
  vietnamese: [{ src: "/food/vietnamese.webp", alt: "Vietnamese beef pho" }],
  mediterranean: [{ src: "/food/mediterranean.webp", alt: "Mediterranean mezze with hummus and falafel" }],
  "middle eastern": [{ src: "/food/middle-eastern.webp", alt: "Middle Eastern shawarma and kebab platter" }],
  american: [{ src: "/food/american.webp", alt: "American cheeseburger and fries" }],
  seafood: [{ src: "/food/seafood.webp", alt: "Seafood platter with salmon, shrimp and mussels" }],
  vegetarian: [{ src: "/food/vegetarian.webp", alt: "Vegetarian grain bowl" }],
};

/** Words that point at one cuisine photo set. Checked against the pipeline's cuisine, then its categories. */
const KEYWORDS: [string, string][] = [
  ["korean", "korean"],
  ["japanese", "japanese"],
  ["sushi", "japanese"],
  ["ramen", "japanese"],
  ["izakaya", "japanese"],
  ["chinese", "chinese"],
  ["dim sum", "chinese"],
  ["dumpling", "chinese"],
  ["indian", "indian"],
  ["mexican", "mexican"],
  ["taco", "mexican"],
  ["italian", "italian"],
  ["pizza", "italian"],
  ["thai", "thai"],
  ["vietnamese", "vietnamese"],
  ["pho", "vietnamese"],
  ["mediterranean", "mediterranean"],
  ["greek", "mediterranean"],
  ["middle eastern", "middle eastern"],
  ["lebanese", "middle eastern"],
  ["turkish", "middle eastern"],
  ["persian", "middle eastern"],
  ["kebab", "middle eastern"],
  ["shawarma", "middle eastern"],
  ["american", "american"],
  ["burger", "american"],
  ["steak", "american"],
  ["barbecue", "american"],
  ["diner", "american"],
  ["seafood", "seafood"],
  ["fish", "seafood"],
  ["vegetarian", "vegetarian"],
  ["vegan", "vegetarian"],
];

export type ImageInput = {
  id?: string;
  restaurant_id?: string;
  name: string;
  cuisine?: string | null;
  categories?: string[];
  image_url?: string | null;
};

/**
 * Restaurant photo from the provider first, then a cuisine photo, then a generic one.
 * The same restaurant id always gets the same picture.
 */
export function getRestaurantImage(restaurant: ImageInput): FoodImage {
  const provided = safeExternalUrl(restaurant.image_url);
  if (provided) {
    return { src: provided, alt: `Photo of ${restaurant.name}`, representative: false, source: "provider" };
  }
  return getCuisineImage(restaurant);
}

/** Fallback used directly when a provider photo fails to load. */
export function getCuisineImage(restaurant: ImageInput): FoodImage {
  const key = cuisineKey(restaurant);
  const options = key ? PHOTOS[key] : null;
  if (!options) return { ...GENERIC, representative: true, source: "generic" };
  const seed = restaurant.id || restaurant.restaurant_id || restaurant.name;
  const photo = options[hash(seed) % options.length];
  return { ...photo, representative: true, source: "cuisine" };
}

export function cuisineKey(restaurant: Pick<ImageInput, "cuisine" | "categories">) {
  for (const value of [restaurant.cuisine, ...(restaurant.categories ?? [])]) {
    if (typeof value !== "string") continue;
    const text = value.toLowerCase();
    const match = KEYWORDS.find(([word]) => new RegExp(`\\b${word}`).test(text));
    if (match) return match[1];
  }
  return null;
}

function hash(text: string) {
  let value = 2166136261;
  for (let index = 0; index < text.length; index += 1) {
    value ^= text.charCodeAt(index);
    value = Math.imul(value, 16777619);
  }
  return value >>> 0;
}

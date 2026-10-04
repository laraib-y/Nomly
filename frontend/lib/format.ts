export const NOT_AVAILABLE = "Not available for now";

const PLACEHOLDER_TEXT = new Set(["null", "undefined", "n/a", "na", "none", "-"]);
const GENERIC_CUISINE = new Set(["restaurant", "restaurants", "food", "dinner", "catering"]);

/** Only a provider price level 1-4 becomes "$" to "$$$$". Anything else is unknown, never guessed. */
export function formatPrice(price: unknown) {
  if (typeof price !== "number" || !Number.isInteger(price) || price < 1 || price > 4) return null;
  return "$".repeat(price);
}

export function formatRating(rating: unknown) {
  if (typeof rating !== "number" || !Number.isFinite(rating) || rating < 0 || rating > 5) return null;
  return rating.toFixed(1);
}

/** Provider addresses often start with the place name; the card already shows it. */
export function formatAddress(address: unknown, name?: string) {
  const text = cleanText(address);
  if (!text || !name) return text;
  const prefix = `${name.trim()}, `;
  return text.toLowerCase().startsWith(prefix.toLowerCase()) && text.length > prefix.length ? text.slice(prefix.length) : text;
}

/** Cuisine from the pipeline, plus at most one extra category. "Restaurant" alone means unknown. */
export function formatCuisine(cuisine: unknown, categories: unknown = []) {
  const labels: string[] = [];
  for (const value of [cuisine, ...(Array.isArray(categories) ? categories : [])]) {
    const label = cleanText(value);
    if (!label || GENERIC_CUISINE.has(label.toLowerCase())) continue;
    if (!labels.some((item) => item.toLowerCase() === label.toLowerCase())) labels.push(label);
  }
  return labels.length ? labels.slice(0, 2).join(" · ") : null;
}

export function formatPhone(phone: unknown) {
  const text = cleanText(phone);
  if (!text || !/^\+?[\d\s().-]+$/.test(text)) return null;
  const digits = text.replace(/\D/g, "");
  if (digits.length < 7 || digits.length > 15) return null;
  return { display: text, href: `tel:${text.startsWith("+") ? "+" : ""}${digits}` };
}

/** Returns a URL only for plain http(s) links. javascript:, data:, file: and malformed values give null. */
export function safeExternalUrl(value: unknown) {
  const text = cleanText(value);
  if (!text || /\s/.test(text)) return null;
  let url: URL;
  try {
    url = new URL(text);
  } catch {
    return null;
  }
  if ((url.protocol !== "https:" && url.protocol !== "http:") || !url.hostname || url.username || url.password) return null;
  return url.href;
}

export function formatWebsite(website: unknown) {
  const href = safeExternalUrl(website);
  if (!href) return null;
  return { href, label: new URL(href).hostname.replace(/^www\./, "") };
}

/** Map link for the restaurant's own provider coordinates. */
export function mapUrl(latitude: unknown, longitude: unknown) {
  if (typeof latitude !== "number" || typeof longitude !== "number") return null;
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;
  if (Math.abs(latitude) > 90 || Math.abs(longitude) > 180 || (latitude === 0 && longitude === 0)) return null;
  return `https://www.google.com/maps/search/?api=1&query=${latitude},${longitude}`;
}

export type RestaurantInfoInput = {
  name: string;
  cuisine?: string | null;
  categories?: string[];
  price?: number | null;
  rating?: number | null;
  address?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  phone?: string | null;
  website?: string | null;
};

export function describeRestaurant(restaurant: RestaurantInfoInput) {
  return {
    cuisine: formatCuisine(restaurant.cuisine, restaurant.categories),
    price: formatPrice(restaurant.price),
    rating: formatRating(restaurant.rating),
    address: formatAddress(restaurant.address, restaurant.name),
    map: mapUrl(restaurant.latitude, restaurant.longitude),
    phone: formatPhone(restaurant.phone),
    website: formatWebsite(restaurant.website),
  };
}

export function cuisineWash(cuisine: string | null) {
  const palette = ["#dce6cf", "#f3ddb0", "#e7e4d8", "#dce5dc", "#f0e0d7", "#e6e4cf"];
  const seed = (cuisine || "Dinner").charCodeAt(0);
  return palette[seed % palette.length];
}

function cleanText(value: unknown) {
  if (typeof value !== "string") return null;
  const text = value.trim();
  if (!text || PLACEHOLDER_TEXT.has(text.toLowerCase())) return null;
  return text;
}

export function formatPrice(price: number | null) {
  if (!price) return null;
  return "$".repeat(Math.min(4, Math.max(1, price)));
}

export function formatRating(rating: number | null) {
  if (rating == null) return null;
  return `⭐ ${rating.toFixed(1)}`;
}

export function cuisineWash(cuisine: string | null) {
  const palette = ["#dce6cf", "#f3ddb0", "#e7e4d8", "#dce5dc", "#f0e0d7", "#e6e4cf"];
  const seed = (cuisine || "Dinner").charCodeAt(0);
  return palette[seed % palette.length];
}

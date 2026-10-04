export function formatPrice(price: number | null) {
  if (!price) return null;
  return "$".repeat(Math.min(4, Math.max(1, price)));
}

export function formatRating(rating: number | null) {
  if (rating == null) return null;
  return `⭐ ${rating.toFixed(1)}`;
}

export function cuisineWash(cuisine: string | null) {
  const palette = ["#f0d3c2", "#dce6cf", "#f3ddb0", "#d9e2f2", "#ead8ee", "#f6d6cf"];
  const seed = (cuisine || "Dinner").charCodeAt(0);
  return palette[seed % palette.length];
}

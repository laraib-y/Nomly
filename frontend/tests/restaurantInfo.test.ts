import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

const format = await import("../lib/format.ts");
const { getRestaurantImage, getCuisineImage, cuisineKey } = await import("../lib/foodImages.ts");
const { NOT_AVAILABLE, describeRestaurant, formatPhone, formatPrice, formatRating, formatAddress, formatWebsite, formatCuisine, safeExternalUrl, mapUrl } = format;

const full = {
  name: "DooBoo",
  cuisine: "Korean",
  categories: ["Korean", "Barbecue"],
  price: 2,
  rating: 4.7,
  address: "4500 Kingsway, Burnaby, BC",
  latitude: 49.2268,
  longitude: -123.0031,
  phone: "+1 604-555-0134",
  website: "https://dooboo.example.com/menu",
};

test("fallback wording is exactly 'Not available for now'", () => {
  assert.equal(NOT_AVAILABLE, "Not available for now");
});

test("every field renders when the provider supplied it", () => {
  const info = describeRestaurant(full);
  assert.equal(info.cuisine, "Korean · Barbecue");
  assert.equal(info.price, "$$");
  assert.equal(info.rating, "4.7");
  assert.equal(info.address, "4500 Kingsway, Burnaby, BC");
  assert.deepEqual(info.phone, { display: "+1 604-555-0134", href: "tel:+16045550134" });
  assert.deepEqual(info.website, { href: "https://dooboo.example.com/menu", label: "dooboo.example.com" });
  assert.equal(info.map, "https://www.google.com/maps/search/?api=1&query=49.2268,-123.0031");
});

test("missing, null and empty fields become null so the UI shows the fallback", () => {
  const info = describeRestaurant({ name: "Bare", cuisine: null, price: null, rating: null, address: "", phone: "  ", website: null });
  assert.deepEqual(info, { cuisine: null, price: null, rating: null, address: null, map: null, phone: null, website: null });
  const undefinedInfo = describeRestaurant({ name: "Bare" });
  assert.deepEqual(undefinedInfo, info);
});

test("placeholder strings from data are never shown", () => {
  for (const value of ["null", "undefined", "N/A", "none"]) {
    assert.equal(formatAddress(value), null);
    assert.equal(formatPhone(value), null);
    assert.equal(formatCuisine(value), null);
  }
});

test("address drops a leading copy of the restaurant name but keeps the rest", () => {
  assert.equal(formatAddress("DooBoo, 6907 Kingsway, Burnaby, BC", "DooBoo"), "6907 Kingsway, Burnaby, BC");
  assert.equal(formatAddress("6907 Kingsway, Burnaby, BC", "DooBoo"), "6907 Kingsway, Burnaby, BC");
  assert.equal(formatAddress("DooBoo", "DooBoo"), "DooBoo");
});

test("price only from a real 1-4 level, never guessed", () => {
  assert.equal(formatPrice(1), "$");
  assert.equal(formatPrice(4), "$$$$");
  for (const value of [0, 5, 2.5, -1, null, undefined, "2", Number.NaN]) assert.equal(formatPrice(value), null);
});

test("rating only from a real 0-5 number", () => {
  assert.equal(formatRating(4.66), "4.7");
  assert.equal(formatRating(0), "0.0");
  for (const value of [6, -1, null, undefined, "4.5", Number.NaN]) assert.equal(formatRating(value), null);
});

test("cuisine 'Restaurant' alone counts as unknown and categories are not duplicated", () => {
  assert.equal(formatCuisine("Restaurant"), null);
  assert.equal(formatCuisine("Japanese", ["Japanese", "Sushi", "Ramen"]), "Japanese · Sushi");
  assert.equal(formatCuisine(null, ["Thai"]), "Thai");
});

test("phone exists, missing, and malformed", () => {
  assert.deepEqual(formatPhone("(604) 555-0134"), { display: "(604) 555-0134", href: "tel:6045550134" });
  assert.equal(formatPhone(null), null);
  assert.equal(formatPhone(""), null);
  assert.equal(formatPhone("123"), null);
  assert.equal(formatPhone("call us"), null);
  assert.equal(formatPhone("javascript:alert(1)"), null);
});

test("unsafe or malformed website URLs are rejected", () => {
  for (const value of [
    "javascript:alert(1)",
    " JavaScript:alert(document.cookie)",
    "data:text/html,<script>alert(1)</script>",
    "file:///etc/passwd",
    "ftp://example.com",
    "https://user:pass@example.com",
    "not a url",
    "example.com",
    "",
    null,
    undefined,
    42,
  ]) {
    assert.equal(safeExternalUrl(value), null, String(value));
    assert.equal(formatWebsite(value), null, String(value));
  }
  assert.equal(safeExternalUrl("http://example.com/a"), "http://example.com/a");
});

test("map link needs real coordinates and uses only the restaurant's own point", () => {
  assert.equal(mapUrl(null, -123), null);
  assert.equal(mapUrl(49.2, undefined), null);
  assert.equal(mapUrl(999, 0), null);
  assert.equal(mapUrl(0, 0), null);
  assert.match(mapUrl(49.2, -123.1) ?? "", /query=49\.2,-123\.1$/);
});

test("provider image wins over the cuisine fallback", () => {
  const image = getRestaurantImage({ id: "r1", name: "DooBoo", cuisine: "Korean", image_url: "https://images.example.com/dooboo.jpg" });
  assert.equal(image.src, "https://images.example.com/dooboo.jpg");
  assert.equal(image.representative, false);
  assert.equal(image.source, "provider");
  assert.equal(image.alt, "Photo of DooBoo");
});

test("unsafe provider image falls back to the cuisine photo", () => {
  const image = getRestaurantImage({ id: "r1", name: "DooBoo", cuisine: "Korean", image_url: "javascript:alert(1)" });
  assert.equal(image.source, "cuisine");
  assert.match(image.src, /^\/food\/korean-\d\.webp$/);
});

test("cuisine photo is chosen from the pipeline's cuisine and categories", () => {
  const cases: [string | null, string[], RegExp][] = [
    ["Japanese", [], /\/food\/japanese-\d\.webp$/],
    ["Korean", [], /\/food\/korean-\d\.webp$/],
    ["Chinese", [], /\/food\/chinese\.webp$/],
    ["Indian", [], /\/food\/indian\.webp$/],
    ["Mexican", [], /\/food\/mexican\.webp$/],
    ["Pizza", [], /\/food\/italian\.webp$/],
    ["Thai", [], /\/food\/thai\.webp$/],
    ["Vietnamese", [], /\/food\/vietnamese\.webp$/],
    ["Greek", [], /\/food\/mediterranean\.webp$/],
    ["Burgers", [], /\/food\/american\.webp$/],
    ["Seafood", [], /\/food\/seafood\.webp$/],
    ["Vegetarian", [], /\/food\/vegetarian\.webp$/],
    ["Restaurant", ["Lebanese"], /\/food\/middle-eastern\.webp$/],
  ];
  for (const [cuisine, categories, expected] of cases) {
    const image = getRestaurantImage({ id: "x", name: "Place", cuisine, categories });
    assert.match(image.src, expected, String(cuisine));
    assert.equal(image.representative, true);
    assert.equal(image.source, "cuisine");
  }
});

test("unknown or missing cuisine uses the generic food photo", () => {
  for (const cuisine of ["Restaurant", "French", null]) {
    const image = getRestaurantImage({ id: "x", name: "Place", cuisine });
    assert.equal(image.src, "/food/generic.webp");
    assert.equal(image.source, "generic");
    assert.equal(image.representative, true);
  }
});

test("the same restaurant always gets the same photo, on the deck and on results", () => {
  const onDeck = getRestaurantImage({ id: "abc-123", name: "Han River BBQ", cuisine: "Korean" });
  const again = getRestaurantImage({ id: "abc-123", name: "Han River BBQ", cuisine: "Korean" });
  const onResults = getCuisineImage({ restaurant_id: "abc-123", name: "Han River BBQ", cuisine: "Korean" });
  assert.equal(onDeck.src, again.src);
  assert.equal(onDeck.src, onResults.src);
  const used = new Set(Array.from({ length: 20 }, (_, index) => getRestaurantImage({ id: `id-${index}`, name: "K", cuisine: "Korean" }).src));
  assert.equal(used.size, 2, "both Korean photos are used across different restaurants");
});

test("cuisine matching does not guess from restaurant names", () => {
  assert.equal(cuisineKey({ cuisine: null, categories: [] }), null);
  const image = getRestaurantImage({ id: "x", name: "Sushi Palace", cuisine: null });
  assert.equal(image.source, "generic");
});

test("every image has meaningful alt text and every photo file exists", () => {
  const keys = ["Korean", "Japanese", "Chinese", "Indian", "Mexican", "Italian", "Thai", "Vietnamese", "Mediterranean", "Lebanese", "Burgers", "Seafood", "Vegetarian", null];
  for (const cuisine of keys) {
    for (const id of ["a", "b", "c", "d"]) {
      const image = getRestaurantImage({ id, name: "Place", cuisine });
      assert.ok(image.alt.length > 8);
      assert.doesNotMatch(image.alt, /^(image|photo|restaurant image)$/i);
      assert.ok(statSync(join("public", image.src)).size > 1000, image.src);
    }
  }
});

function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? sources(path) : /\.(ts|tsx)$/.test(name) ? [path] : [];
  });
}

test("frontend source never references provider keys or calls Geoapify directly", () => {
  for (const file of [...sources("app"), ...sources("components"), ...sources("lib")]) {
    const text = readFileSync(file, "utf8");
    assert.doesNotMatch(text, /GEOAPIFY|ELEVENLABS_API_KEY|GEMINI_API_KEY|NEXT_PUBLIC_[A-Z_]*KEY|api\.geoapify\.com|apiKey=/, file);
  }
});

test("missing rating and price are hidden instead of showing fallback text", () => {
  const text = readFileSync("components/RestaurantInfo.tsx", "utf8");
  assert.match(text, /if \(!info\.rating && !info\.price\) return null;/);
  assert.doesNotMatch(text, /Rating · |Price range · /);
});

test("restaurant cards no longer use the crocodile placeholder", () => {
  for (const file of ["components/RestaurantCard.tsx", "components/RestaurantInfo.tsx", "components/ResultsRoom.tsx", "components/ResultsDisplay.tsx"]) {
    assert.doesNotMatch(readFileSync(file, "utf8"), /IMG_8293/, file);
  }
});

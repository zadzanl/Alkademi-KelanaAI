/**
 * Shared category-to-style mapping for trip category badges and avatars.
 * Used by both TripCard and TripDetailView to ensure consistent visual treatment.
 *
 * Mapping rules:
 * - "backpacker" or "budget" → emerald (green) tint
 * - "luxury" → amber (gold) tint
 * - everything else (including "standard", "mediocre", unknown) → teal tint
 */

export interface CategoryStyle {
  avatar: string;
  badge: string;
}

export function categoryStyle(category: string): CategoryStyle {
  const normalized = (category || "").toLowerCase();

  if (normalized.includes("backpacker") || normalized.includes("budget")) {
    return {
      avatar:
        "bg-emerald-500/10 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-300",
      badge:
        "bg-emerald-100 text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-200 border-emerald-200 dark:border-emerald-800/40",
    };
  }

  if (normalized.includes("luxury")) {
    return {
      avatar:
        "bg-amber-500/10 text-amber-900 dark:bg-amber-400/20 dark:text-amber-300",
      badge:
        "bg-amber-100 text-amber-900 dark:bg-amber-950/60 dark:text-amber-200 border-amber-200 dark:border-amber-800/40",
    };
  }

  return {
    avatar:
      "bg-indigo-light text-teal-900 dark:bg-indigo-light/30 dark:text-teal-300",
    badge:
      "bg-teal-100 text-teal-900 dark:bg-teal-950/60 dark:text-teal-200 border-teal-200 dark:border-teal-800/40",
  };
}

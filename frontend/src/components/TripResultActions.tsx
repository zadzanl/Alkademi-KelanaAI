"use client";

import Link from "next/link";
import { useState } from "react";
import type { TripResponse } from "../types/trip.ts";
import { formatMoney } from "../lib/formatMoney.ts";

function shareText(trip: TripResponse): string {
  const places = trip.recommended_places.length
    ? trip.recommended_places.join(", ")
    : "places selected in the plan";
  const home = `${window.location.origin}/`;
  return `My ${trip.days}-day ${trip.destination} trip (${trip.country})\nBudget: ${formatMoney(Number(trip.budget), trip.currency)}\nStyle: ${trip.category}\nPlaces: ${places}\nPlan yours: ${home}`;
}

export function TripResultActions({ trip }: { trip: TripResponse }) {
  const [shared, setShared] = useState(false);
  const draft = `Help me refine my ${trip.days}-day ${trip.destination} trip with a ${formatMoney(Number(trip.budget), trip.currency)} budget.`;

  const share = () => {
    const text = shareText(trip);
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank", "noopener,noreferrer");
    setShared(true);
  };

  return (
    <div className="mt-8 flex flex-wrap gap-3 border-t border-surface-rule pt-6">
      <Link
        href={`/chat?prefill=${encodeURIComponent(draft)}`}
        className="min-h-11 rounded-surface bg-terracotta px-4 py-3 text-sm font-bold text-white focus-visible:outline-focus-ring"
      >
        Refine with KelanaAI
      </Link>
      <Link
        href="/#planner"
        className="min-h-11 rounded-surface border border-control px-4 py-3 text-sm font-bold text-ink focus-visible:outline-focus-ring"
      >
        Plan another trip
      </Link>
      <button
        type="button"
        onClick={share}
        className="min-h-11 rounded-surface border border-control px-4 py-3 text-sm font-bold text-ink focus-visible:outline-focus-ring"
      >
        Share as text
      </button>
      {shared && (
        <span role="status" className="self-center text-sm text-muted-ink">
          Share opened.
        </span>
      )}
    </div>
  );
}

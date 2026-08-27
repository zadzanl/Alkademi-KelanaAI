import type { Metadata } from "next";
import Link from "next/link";
import { getTrips } from "../../services/tripService.ts";
import { TripCard } from "../../components/TripCard.tsx";
import { EmptyState } from "../../components/EmptyState.tsx";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Trip History | KelanaAI",
  description:
    "Browse and review all previously created travel plans and AI itineraries.",
};

export default async function TripsPage() {
  const trips = await getTrips();

  return (
    <div className="min-h-screen bg-paper text-ink">
      <main className="mx-auto max-w-5xl px-5 py-12 sm:px-8 sm:py-16">
        {/* Top Action Bar */}
        <div className="mb-8 flex items-center justify-between border-b border-rule pb-4">
          <Link
            href="/"
            className="inline-flex min-h-[44px] items-center text-sm font-semibold text-muted-ink transition-colors hover:text-ink focus-visible:outline-terracotta"
          >
            ← Back to Planner
          </Link>
          <Link
            href="/#planner"
            className="inline-flex min-h-[44px] items-center text-sm font-bold text-terracotta-dark transition-colors hover:underline focus-visible:outline-terracotta"
          >
            + Plan a New Trip
          </Link>
        </div>

        {/* Page Title & Count */}
        <header className="mb-10">
          <div className="flex flex-wrap items-baseline gap-3">
            <h1 className="font-display text-4xl font-normal text-ink sm:text-5xl">
              Trip History
            </h1>
            <span className="rounded-full border border-rule bg-paper-light px-3 py-1 text-xs font-semibold tabular text-muted-ink">
              {trips.length}{" "}
              {trips.length === 1 ? "saved itinerary" : "saved itineraries"}
            </span>
          </div>
          <p className="mt-3 max-w-[60ch] text-base leading-relaxed text-muted-ink sm:text-lg">
            Revisit your previously shaped itineraries, explore deterministic
            daily cost breakdowns, and read AI travel narratives.
          </p>
        </header>

        {/* Content Section */}
        <section aria-label="Saved Itineraries">
          {trips.length === 0 ? (
            <EmptyState headingLevel="h2" />
          ) : (
            <div className="space-y-4">
              {trips.map((trip) => (
                <TripCard key={trip.id} trip={trip} />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

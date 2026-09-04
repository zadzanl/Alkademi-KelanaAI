import type { Metadata } from "next";
import Link from "next/link";
import { getTrips, TripApiError } from "../../services/tripService.ts";
import { TripCard } from "../../components/TripCard.tsx";
import { EmptyState } from "../../components/EmptyState.tsx";
import { Pagination } from "../../components/Pagination.tsx";
import { parseTripId } from "../../lib/safety.ts";
import type { TripListResponse } from "../../types/trip.ts";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "My Trips | KelanaAI",
  description:
    "Browse and review all previously created travel plans and AI itineraries.",
};

type TripsPageProps = {
  searchParams: Promise<{ page?: string }>;
};

export default async function TripsPage({ searchParams }: TripsPageProps) {
  const { page: rawPage } = await searchParams;
  const page = parseTripId(rawPage ?? "1") ?? 1;

  let tripData: TripListResponse | null = null;
  let isUnauthorized = false;

  try {
    tripData = await getTrips(page);
  } catch (error) {
    if (error instanceof TripApiError && (error.kind === "unauthorized" || error.status === 401)) {
      isUnauthorized = true;
    } else {
      throw error;
    }
  }

  const items = tripData?.items ?? [];
  const total = tripData?.total ?? 0;
  const pageSize = tripData?.page_size ?? 10;
  const isOutOfRange = page > 1 && items.length === 0 && total > 0;

  return (
    <div className="min-h-screen bg-paper text-ink">
      <main className="mx-auto max-w-5xl px-5 py-12 sm:px-8 sm:py-16">
        {/* Top Action Bar */}
        <div className="mb-8 flex items-center justify-between border-b border-rule pb-4">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="inline-flex min-h-[44px] items-center text-sm font-semibold text-muted-ink transition-colors hover:text-ink focus-visible:outline-terracotta"
            >
              ← Back to Planner
            </Link>
            <Link
              href="/chat"
              className="inline-flex min-h-[44px] items-center text-sm font-semibold text-terracotta-dark transition-colors hover:underline focus-visible:outline-terracotta"
            >
              💬 Travel Assistant
            </Link>
          </div>
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
              My Trips
            </h1>
            {!isUnauthorized && (
              <span className="rounded-full border border-rule bg-paper-light px-3 py-1 text-xs font-semibold tabular text-muted-ink">
                {total} {total === 1 ? "saved itinerary" : "saved itineraries"}
              </span>
            )}
          </div>
          <p className="mt-3 max-w-[60ch] text-base leading-relaxed text-muted-ink sm:text-lg">
            Revisit your previously shaped itineraries, explore deterministic
            daily cost breakdowns, and read AI travel narratives.
          </p>
        </header>

        {/* Content Section */}
        <section aria-label="Saved Itineraries">
          {isUnauthorized ? (
            <EmptyState
              headingLevel="h2"
              title="Sign in to view your trips"
              description="Your saved travel itineraries are private to your account. Sign in or create an account to view and manage your trips."
              actionText="Sign in to KelanaAI"
              actionHref="/auth"
            />
          ) : total === 0 ? (
            <EmptyState headingLevel="h2" />
          ) : isOutOfRange ? (
            <EmptyState
              headingLevel="h2"
              title="That page is empty"
              description="There are saved itineraries, but none on this page. Return to the beginning of your trips."
              actionText="Back to page 1"
              actionHref="/trips"
            />
          ) : (
            <>
              <div className="space-y-4">
                {items.map((trip) => (
                  <TripCard key={trip.id} trip={trip} />
                ))}
              </div>
              <Pagination page={page} total={total} pageSize={pageSize} />
            </>
          )}
        </section>
      </main>
    </div>
  );
}

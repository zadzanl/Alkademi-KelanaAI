import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { categoryStyle } from "../lib/categoryStyle.ts";
import { markdownComponents } from "../lib/markdownPolicy.ts";
import type { TripResponse } from "../types/trip.ts";

export interface TripDetailViewProps {
  trip: TripResponse;
  /**
   * Heading tag for the trip destination title.
   * Use "h1" on standalone detail pages (/trips/[id]) and "h2" when embedded on /
   * @default "h2"
   */
  headingLevel?: "h1" | "h2";
  /**
   * Whether to display the breadcrumb back-navigation trail.
   * @default false
   */
  showBackLink?: boolean;
  /**
   * Target URL for the back link.
   * @default "/trips"
   */
  backHref?: string;
  /**
   * Text label for the back link.
   * @default "Back to Trip History"
   */
  backLabel?: string;
  className?: string;
}

export function TripDetailView({
  trip,
  headingLevel = "h2",
  showBackLink = false,
  backHref = "/trips",
  backLabel = "Back to Trip History",
  className = "",
}: TripDetailViewProps) {
  const HeadingTag = headingLevel;
  const SubHeadingTag = headingLevel === "h1" ? "h2" : "h3";

  // Format ISO timestamp into deterministic human-readable date
  const formattedDate = trip.created_at
    ? new Date(trip.created_at).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        timeZone: "UTC",
      })
    : null;

  const categoryBadgeClass = categoryStyle(trip.category).badge;

  return (
    <article
      aria-labelledby="trip-detail-heading"
      className={`journal-reveal ${className}`}
    >
      {/* 1. Breadcrumb navigation */}
      {showBackLink && (
        <nav aria-label="Breadcrumb" className="mb-6">
          <ol className="flex flex-wrap items-center gap-2 text-sm font-semibold text-muted-ink">
            <li>
              <Link
                href="/"
                className="transition-colors hover:text-ink focus-visible:outline-terracotta"
              >
                Home
              </Link>
            </li>
            <li aria-hidden="true" className="text-rule">
              /
            </li>
            <li>
              <Link
                href={backHref}
                className="inline-flex items-center gap-1 transition-colors hover:text-terracotta-dark focus-visible:outline-terracotta"
              >
                <span aria-hidden="true">←</span>
                <span>{backLabel}</span>
              </Link>
            </li>
            <li aria-hidden="true" className="text-rule">
              /
            </li>
            <li
              aria-current="page"
              className="max-w-[220px] truncate font-bold text-ink sm:max-w-none"
            >
              {trip.destination}
            </li>
          </ol>
        </nav>
      )}

      {/* 2. Destination Header & Metadata Strip */}
      <header className="border-t border-ink pt-5">
        <div className="grid gap-5 border-b border-rule pb-9 md:grid-cols-[1fr_auto] md:items-end">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-3 text-xs font-semibold text-muted-ink">
              <span className="tabular">Trip #{trip.id}</span>
              {formattedDate && (
                <>
                  <span aria-hidden="true">·</span>
                  <time dateTime={trip.created_at} suppressHydrationWarning>
                    Saved on {formattedDate}
                  </time>
                </>
              )}
            </div>

            <HeadingTag
              id="trip-detail-heading"
              className="font-display wrap-anywhere mt-2 text-[clamp(2.75rem,7vw,4.5rem)] leading-[0.94] tracking-[-0.025em] text-ink"
            >
              {trip.destination}
            </HeadingTag>

            <p className="mt-4 text-lg text-muted-ink">
              {trip.days} {trip.days === 1 ? "day" : "days"} · {trip.travel_month} ·{" "}
              {trip.country}
            </p>
          </div>

          <div className="flex shrink-0 items-center">
            <span
              className={`inline-block rounded-full border px-4 py-1.5 text-sm font-bold tracking-wide uppercase ${categoryBadgeClass}`}
            >
              {trip.category}
            </span>
          </div>
        </div>
      </header>

      {/* 3. Budget & Logistics Cards Grid */}
      <section
        aria-label="Trip Budget and Logistics"
        className="grid gap-0 border-b border-rule lg:grid-cols-[1.35fr_0.8fr_0.65fr]"
      >
        {/* Total Budget */}
        <div className="min-w-0 py-9 lg:border-r lg:border-rule lg:pr-10">
          <p className="text-sm font-semibold text-muted-ink">Total budget</p>
          <p className="font-display tabular wrap-anywhere mt-3 text-[clamp(2.4rem,6vw,5rem)] leading-none text-terracotta-dark">
            {trip.currency} {Number(trip.budget).toLocaleString()}
          </p>
        </div>

        {/* Daily Budget */}
        <div className="min-w-0 border-t border-rule py-9 lg:border-r lg:border-t-0 lg:px-8">
          <p className="text-sm font-semibold text-muted-ink">Daily budget</p>
          <p className="tabular wrap-anywhere mt-3 text-2xl font-bold text-ink">
            {trip.currency} {Number(trip.daily_budget).toLocaleString()}
          </p>
          <p className="mt-1 text-xs text-muted-ink">per day average</p>
        </div>

        {/* Season & Transport DL */}
        <div className="min-w-0 border-t border-rule py-9 lg:border-t-0 lg:pl-8">
          <dl className="space-y-6">
            <div>
              <dt className="text-sm font-semibold text-muted-ink">Season</dt>
              <dd className="wrap-anywhere mt-1 font-bold text-ink">
                {trip.travel_season}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-semibold text-muted-ink">
                Getting around
              </dt>
              <dd className="wrap-anywhere mt-1 font-bold text-ink">
                {trip.recommended_transportation}
              </dd>
            </div>
          </dl>
        </div>
      </section>

      {/* 4. Places & AI Narrative Columns */}
      <div className="grid gap-12 py-12 lg:grid-cols-[0.65fr_1.35fr] lg:gap-20">
        {/* Recommended Places */}
        <section aria-labelledby="places-heading" className="min-w-0">
          <SubHeadingTag
            id="places-heading"
            className="font-display text-3xl leading-none text-ink"
          >
            Places to keep close
          </SubHeadingTag>
          <ol className="mt-7 border-t border-rule">
            {(trip.recommended_places ?? []).map((place, index) => (
              <li
                key={`${place}-${index}`}
                className="wrap-anywhere grid grid-cols-[2rem_1fr] gap-3 border-b border-rule py-4 text-ink"
              >
                <span
                  className="tabular text-sm font-bold text-terracotta-dark"
                  aria-hidden="true"
                >
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="font-semibold">{place}</span>
              </li>
            ))}
          </ol>
        </section>

        {/* AI Itinerary Narrative */}
        <section
          aria-labelledby="itinerary-heading"
          className="min-w-0 border-t border-ink pt-5 lg:border-t-0 lg:pt-0"
        >
          <SubHeadingTag
            id="itinerary-heading"
            className="font-display text-3xl leading-none text-ink"
          >
            AI itinerary
          </SubHeadingTag>

          {trip.ai_recommendation?.trim() ? (
            <div className="journal-prose prose mt-7 max-w-[72ch] text-ink">
              <ReactMarkdown
                components={markdownComponents(SubHeadingTag)}
              >
                {trip.ai_recommendation}
              </ReactMarkdown>
            </div>
          ) : (
            <div
              role="status"
              className="mt-7 border-y border-rule bg-indigo-light px-5 py-4 text-indigo dark:bg-slate-800/80 dark:text-slate-200 dark:border-slate-700"
            >
              <p className="font-semibold">
                AI itinerary unavailable for this trip.
              </p>
              <p className="mt-1 text-sm text-indigo/80 dark:text-slate-400">
                Deterministic summary and places are preserved above.
              </p>
            </div>
          )}
        </section>
      </div>
    </article>
  );
}

import Link from "next/link";
import { categoryStyle } from "../lib/categoryStyle.ts";
import type { TripResponse } from "../types/trip.ts";

type TripCardProps = {
  trip: TripResponse;
};

export function TripCard({ trip }: TripCardProps) {
  const style = categoryStyle(trip.category);

  return (
    <article className="group relative rounded-[4px] border border-rule bg-paper-light p-5 transition-all duration-200 hover:border-ink/40 hover:shadow-md sm:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-4 min-w-0">
          {/* Circular Category-Tinted Avatar */}
          <div
            className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full transition-transform duration-200 group-hover:scale-105 ${style.avatar}`}
            aria-hidden="true"
          >
            <svg
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="1.75"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>

          {/* Heading & Metadata */}
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2.5">
              <h2 className="font-display text-2xl font-normal leading-tight text-ink transition-colors group-hover:text-terracotta-dark sm:text-3xl">
                {trip.destination}
              </h2>
              {trip.country && (
                <span className="text-sm font-medium text-muted-ink">
                  ({trip.country})
                </span>
              )}
              <span
                className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-bold tracking-wide uppercase ${style.badge}`}
              >
                {trip.category}
              </span>
            </div>

            <p className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-ink tabular sm:text-base">
              <span>{trip.days} days</span>
              <span aria-hidden="true">·</span>
              <span className="font-semibold text-ink">
                {trip.currency} {Number(trip.budget).toLocaleString()}
              </span>
              <span aria-hidden="true">·</span>
              <span>{trip.travel_season}</span>
              {trip.travel_month && (
                <>
                  <span aria-hidden="true">·</span>
                  <span>{trip.travel_month}</span>
                </>
              )}
            </p>
          </div>
        </div>

        {/* View Details CTA Button */}
        <div className="flex shrink-0 items-center justify-end pt-2 sm:pt-0">
          <span className="inline-flex items-center gap-1.5 text-sm font-bold text-ink transition-colors group-hover:text-terracotta-dark">
            <span>View Details</span>
            <span
              className="inline-block transition-transform duration-200 group-hover:translate-x-1.5"
              aria-hidden="true"
            >
              →
            </span>
          </span>
        </div>
      </div>

      {/* Accessible Hit Area */}
      <Link
        href={`/trips/${trip.id}`}
        className="absolute inset-0 z-10 rounded-[4px] focus-visible:outline-3 focus-visible:outline-terracotta"
      >
        <span className="sr-only">
          View details for trip to {trip.destination}, {trip.days} days,{" "}
          {trip.currency} {Number(trip.budget).toLocaleString()}
        </span>
      </Link>
    </article>
  );
}

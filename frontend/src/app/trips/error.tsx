"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function TripsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // In production, errors can be logged to telemetry
    console.error("Trip history error boundary caught:", error);
  }, [error]);

  return (
    <main className="mx-auto max-w-2xl px-5 py-20 text-center sm:px-8">
      <div className="rounded-[4px] border border-error/30 bg-paper-light p-8 sm:p-12">
        <p className="tabular text-xs font-bold uppercase tracking-wider text-error">
          Connection Notice
        </p>
        <h1 className="font-display mt-3 text-3xl font-normal text-ink sm:text-4xl">
          Unable to retrieve trip history
        </h1>
        <p className="mx-auto mt-4 max-w-[50ch] text-base leading-relaxed text-muted-ink">
          We could not connect to the trip service. Ensure the backend server
          is running, then try again.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-4">
          <button
            type="button"
            onClick={() => reset()}
            className="inline-flex min-h-11 items-center justify-center rounded-[4px] bg-terracotta px-6 text-sm font-bold text-white transition-colors hover:bg-terracotta-dark focus-visible:outline-indigo"
          >
            Try again
          </button>
          <Link
            href="/"
            className="inline-flex min-h-11 items-center justify-center rounded-[4px] border border-rule bg-paper px-6 text-sm font-bold text-ink transition-colors hover:border-control focus-visible:outline-indigo"
          >
            Back to Planner
          </Link>
        </div>
      </div>
    </main>
  );
}


import Link from "next/link";

export default function TripNotFound() {
  return (
    <div className="min-h-screen bg-paper text-ink">
      <main className="mx-auto max-w-2xl px-5 py-20 text-center sm:px-8">
        <div className="rounded-[4px] border border-rule bg-paper-light p-8 sm:p-12">
          <p className="tabular text-xs font-bold uppercase tracking-wider text-terracotta-dark">
            404 — Not Found
          </p>
          <h1 className="font-display mt-3 text-3xl font-normal text-ink sm:text-4xl">
            Itinerary snapshot not found
          </h1>
          <p className="mx-auto mt-4 max-w-[50ch] text-base leading-relaxed text-muted-ink">
            The requested trip itinerary does not exist, has an invalid
            identifier, or was removed.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Link
              href="/trips"
              className="inline-flex min-h-11 items-center justify-center rounded-[4px] bg-terracotta px-6 text-sm font-bold text-white transition-colors hover:bg-terracotta-dark focus-visible:outline-indigo"
            >
              ← View All Saved Trips
            </Link>
            <Link
              href="/"
              className="inline-flex min-h-11 items-center justify-center rounded-[4px] border border-rule bg-paper px-6 text-sm font-bold text-ink transition-colors hover:border-control focus-visible:outline-indigo"
            >
              Plan a New Trip
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}


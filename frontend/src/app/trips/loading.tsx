export default function TripsLoading() {
  return (
    <div
      className="min-h-screen bg-paper text-ink"
      aria-busy="true"
      aria-label="Loading trip history"
    >
      <main className="mx-auto max-w-5xl px-5 py-12 sm:px-8 sm:py-16">
        {/* Top Action Bar Skeleton */}
        <div className="mb-8 flex items-center justify-between border-b border-rule pb-4 motion-safe:animate-pulse">
          <div className="h-4 w-28 rounded bg-rule/50" />
          <div className="h-4 w-32 rounded bg-rule/50" />
        </div>

        {/* Header Skeleton */}
        <div className="mb-10 space-y-3 motion-safe:animate-pulse">
          <div className="flex items-baseline gap-3">
            <div className="h-10 w-56 rounded bg-rule/60 sm:h-12 sm:w-72" />
            <div className="h-6 w-32 rounded-full bg-rule/40" />
          </div>
          <div className="space-y-2">
            <div className="h-4 w-full max-w-[55ch] rounded bg-rule/40" />
            <div className="h-4 w-4/5 max-w-[45ch] rounded bg-rule/40" />
          </div>
        </div>

        {/* Card Skeletons */}
        <div className="space-y-4 motion-safe:animate-pulse">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="flex flex-col justify-between gap-4 rounded-[4px] border border-rule bg-paper-light p-5 sm:flex-row sm:items-center sm:p-6"
            >
              <div className="flex min-w-0 flex-1 items-start gap-4">
                <div className="h-12 w-12 shrink-0 rounded-full bg-rule/50" />
                <div className="flex-1 space-y-2">
                  <div className="h-6 w-1/3 rounded bg-rule/60" />
                  <div className="h-4 w-2/3 rounded bg-rule/40" />
                </div>
              </div>
              <div className="h-5 w-24 rounded bg-rule/40" />
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}


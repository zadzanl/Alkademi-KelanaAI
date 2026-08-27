export default function TripDetailLoading() {
  return (
    <div
      className="min-h-screen bg-paper text-ink"
      aria-busy="true"
      aria-label="Loading trip details"
    >
      <main className="mx-auto max-w-6xl px-5 py-12 sm:px-8">
        <div className="space-y-8 motion-safe:animate-pulse">
          {/* Breadcrumb Skeleton */}
          <div className="flex items-center gap-2 border-b border-rule pb-4">
            <div className="h-4 w-12 rounded bg-rule/50" />
            <div className="h-4 w-3 rounded bg-rule/30" />
            <div className="h-4 w-32 rounded bg-rule/50" />
            <div className="h-4 w-3 rounded bg-rule/30" />
            <div className="h-4 w-24 rounded bg-rule/40" />
          </div>

          {/* Destination Header Skeleton */}
          <div className="grid gap-5 border-b border-rule pb-9 md:grid-cols-[1fr_auto] md:items-end">
            <div className="space-y-4">
              <div className="h-14 w-3/4 max-w-md rounded bg-rule/60 sm:h-20" />
              <div className="h-5 w-64 rounded bg-rule/40" />
            </div>
            <div className="h-8 w-28 rounded-full bg-rule/50" />
          </div>

          {/* Financial & Logistics Grid Skeleton */}
          <div className="grid gap-0 border-b border-rule lg:grid-cols-[1.35fr_0.8fr_0.65fr]">
            <div className="py-9 lg:border-r lg:border-rule lg:pr-10 space-y-3">
              <div className="h-4 w-24 rounded bg-rule/40" />
              <div className="h-12 w-48 rounded bg-rule/60" />
            </div>
            <div className="border-t border-rule py-9 lg:border-r lg:border-t-0 lg:px-8 space-y-3">
              <div className="h-4 w-24 rounded bg-rule/40" />
              <div className="h-8 w-36 rounded bg-rule/50" />
            </div>
            <div className="border-t border-rule py-9 lg:border-t-0 lg:pl-8 space-y-4">
              <div className="space-y-1">
                <div className="h-3 w-16 rounded bg-rule/40" />
                <div className="h-5 w-28 rounded bg-rule/50" />
              </div>
              <div className="space-y-1">
                <div className="h-3 w-24 rounded bg-rule/40" />
                <div className="h-5 w-32 rounded bg-rule/50" />
              </div>
            </div>
          </div>

          {/* Places & Narrative Split Skeleton */}
          <div className="grid gap-12 py-12 lg:grid-cols-[0.65fr_1.35fr] lg:gap-20">
            <div className="space-y-4">
              <div className="h-8 w-44 rounded bg-rule/60" />
              <div className="space-y-3 border-t border-rule pt-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex items-center gap-3 border-b border-rule py-3">
                    <div className="h-4 w-6 rounded bg-rule/40" />
                    <div className="h-4 w-40 rounded bg-rule/50" />
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-4 border-t border-ink pt-5">
              <div className="h-8 w-36 rounded bg-rule/60" />
              <div className="space-y-3 pt-2">
                <div className="h-4 w-full rounded bg-rule/40" />
                <div className="h-4 w-5/6 rounded bg-rule/40" />
                <div className="h-4 w-4/5 rounded bg-rule/40" />
                <div className="h-4 w-full rounded bg-rule/30" />
                <div className="h-4 w-2/3 rounded bg-rule/30" />
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}


import Link from "next/link";

type EmptyStateProps = {
  title?: string;
  description?: string;
  actionText?: string;
  actionHref?: string;
  headingLevel?: "h2" | "h3";
};

export function EmptyState({
  title = "No saved itineraries yet",
  description = "Every memorable journey begins with a single destination. Plan your first trip to generate a grounded itinerary, daily budget, and AI narrative.",
  actionText = "Plan your first trip",
  actionHref = "/",
  headingLevel = "h2",
}: EmptyStateProps) {
  const HeadingTag = headingLevel;

  return (
    <div className="journal-reveal rounded-[4px] border-2 border-dashed border-rule bg-paper-light/60 px-6 py-16 text-center sm:px-12 sm:py-20">
      <div
        className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-terracotta/10 text-terracotta-dark dark:bg-terracotta/20"
        aria-hidden="true"
      >
        <svg
          className="h-8 w-8"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth="1.75"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
          />
        </svg>
      </div>

      <HeadingTag className="font-display mt-6 text-3xl font-normal text-ink sm:text-4xl">
        {title}
      </HeadingTag>

      <p className="mx-auto mt-4 max-w-[52ch] text-base leading-relaxed text-muted-ink sm:text-lg">
        {description}
      </p>

      <div className="mt-8 flex justify-center">
        <Link
          href={actionHref}
          className="inline-flex min-h-12 items-center justify-center rounded-[4px] bg-terracotta px-6 py-3 text-base font-bold text-white transition-colors duration-150 hover:bg-terracotta-dark focus-visible:outline-terracotta"
        >
          {actionText}
          <span className="ml-2" aria-hidden="true">
            →
          </span>
        </Link>
      </div>
    </div>
  );
}

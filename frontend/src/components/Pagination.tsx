import Link from "next/link";

type PaginationProps = {
  page: number;
  total: number;
  pageSize: number;
};

export function Pagination({ page, total, pageSize }: PaginationProps) {
  const totalPages = Math.ceil(total / pageSize);

  if (totalPages <= 1) {
    return null;
  }

  const visiblePages = Array.from(
    new Set([
      1,
      ...Array.from({ length: 5 }, (_, index) => page - 2 + index),
      totalPages,
    ]),
  )
    .filter((pageNumber) => pageNumber >= 1 && pageNumber <= totalPages)
    .sort((a, b) => a - b);

  const linkClass =
    "inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-[4px] border border-rule bg-paper-light px-3 text-sm font-semibold text-muted-ink transition-colors hover:border-terracotta hover:text-ink focus-visible:outline-terracotta";
  const currentClass =
    "inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-[4px] border border-terracotta bg-terracotta px-3 text-sm font-bold text-white";
  const disabledClass =
    "inline-flex min-h-[44px] items-center justify-center rounded-[4px] border border-rule px-4 text-sm font-semibold text-control opacity-60";

  return (
    <nav
      aria-label="Pagination"
      className="mt-8 flex flex-wrap items-center justify-center gap-2 border-t border-rule pt-6"
    >
      {page === 1 ? (
        <span className={disabledClass} aria-disabled="true">
          Previous
        </span>
      ) : (
        <Link href={`/trips?page=${page - 1}`} className={linkClass}>
          Previous
        </Link>
      )}

      <div className="flex flex-wrap items-center justify-center gap-2">
        {visiblePages.map((pageNumber, index) => {
          const previousPage = visiblePages[index - 1];
          const hasGap = previousPage !== undefined && pageNumber - previousPage > 1;

          return (
            <span key={pageNumber} className="contents">
              {hasGap ? (
                <span className="px-1 text-muted-ink" aria-hidden="true">
                  …
                </span>
              ) : null}
              {pageNumber === page ? (
                <Link
                  href={`/trips?page=${pageNumber}`}
                  className={currentClass}
                  aria-current="page"
                  aria-label={`Page ${pageNumber}, current page`}
                >
                  {pageNumber}
                </Link>
              ) : (
                <Link
                  href={`/trips?page=${pageNumber}`}
                  className={linkClass}
                  aria-label={`Page ${pageNumber}`}
                >
                  {pageNumber}
                </Link>
              )}
            </span>
          );
        })}
      </div>

      {page === totalPages ? (
        <span className={disabledClass} aria-disabled="true">
          Next
        </span>
      ) : (
        <Link href={`/trips?page=${page + 1}`} className={linkClass}>
          Next
        </Link>
      )}
    </nav>
  );
}
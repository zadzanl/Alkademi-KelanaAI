type RevalidatePath = (path: string) => void;
type CacheLoader = () => Promise<{ revalidatePath: RevalidatePath }>;

function isNodeTestImportError(error: unknown): boolean {
  if (!process.env.NODE_TEST_CONTEXT || !error || typeof error !== "object") {
    return false;
  }

  const code = "code" in error ? (error as { code?: unknown }).code : undefined;
  const message = error instanceof Error ? error.message : "";
  return code === "ERR_MODULE_NOT_FOUND" && /next[\\/]cache/.test(message);
}

/**
 * Invalidates the trip-history page after a successful mutation.
 *
 * Node's dependency-free test runner cannot resolve Next's `next/cache` ESM
 * subpath on Windows or POSIX. Only that import failure is ignored, and only
 * when Node marks the process as a test child. Runtime `revalidatePath` errors
 * always propagate. The injectable loader exists solely for focused tests.
 */
export async function invalidateTripsCache(
  loadCache: CacheLoader = () => import("next/cache"),
): Promise<void> {
  let cache: { revalidatePath: RevalidatePath };
  try {
    cache = await loadCache();
  } catch (error) {
    if (isNodeTestImportError(error)) {
      return;
    }
    throw error;
  }

  cache.revalidatePath("/trips");
}
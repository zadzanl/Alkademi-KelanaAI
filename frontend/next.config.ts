import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Next 15.5 still reads this option from the experimental namespace.
  // Keeping it here avoids silently falling back to the 1 MB default.
  experimental: { serverActions: { bodySizeLimit: "25mb" } },
  // Dev-server file watching: poll every 1s instead of relying solely on OS
  // change events, which can be missed on Windows (atomic/safe saves replace
  // the file via rename). Applies to both Turbopack and webpack dev servers.
  // Known ceiling: slight CPU cost while `next dev` runs; delete this block
  // if native watch events prove reliable on this machine.
  watchOptions: { pollIntervalMs: 1000 },
};

export default nextConfig;

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Next 15.5 still reads this option from the experimental namespace.
  // Keeping it here avoids silently falling back to the 1 MB default.
  experimental: { serverActions: { bodySizeLimit: "25mb" } },
};

export default nextConfig;

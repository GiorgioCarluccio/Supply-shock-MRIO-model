/** @type {import('next').NextConfig} */

// Base path for deployment under a sub-directory (e.g. GitHub Pages project
// site at /<repo>). Empty for local dev and root deployments.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

const nextConfig = {
  reactStrictMode: true,

  // Static demonstrative app: emit a fully static site (out/) with no server
  // runtime. The dashboard reads precomputed JSON/GeoJSON from /public/data.
  output: "export",

  // GitHub Pages has no image-optimization server, so serve images as-is.
  images: { unoptimized: true },

  // Clean folder URLs (e.g. /regional/index.html) so static hosts resolve routes.
  trailingSlash: true,

  basePath: basePath || undefined,
  assetPrefix: basePath || undefined,

  eslint: {
    // Lint is run separately; do not block the demo build on lint.
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;

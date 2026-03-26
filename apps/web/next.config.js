/** @type {import('next').NextConfig} */
const nextConfig = {
  // Produces a self-contained build in .next/standalone
  // This lets us run `node .next/standalone/server.js` without npm
  output: "standalone",

  async rewrites() {
    // INTERNAL_API_URL is server-only (no NEXT_PUBLIC_ prefix) — never exposed to browser.
    // Browser requests arrive as /api/:path* and are proxied to the backend here.
    const apiUrl = process.env.INTERNAL_API_URL || "http://127.0.0.1:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Produces a self-contained build in .next/standalone
  // This lets us run `node .next/standalone/server.js` without npm
  output: "standalone",

  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;

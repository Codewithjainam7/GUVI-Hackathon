import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // reactCompiler: true, // Temporarily disable experimental compiler if causing issues
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.BACKEND_URL || 'http://localhost:8088'}/api/:path*`, // Proxy to Backend (Cloud or Local)
      },
      // Allow Vercel to handle API routes directly if hosted there
      {
        source: '/api/v1/:path*',
        destination: `${process.env.BACKEND_URL || 'http://localhost:8088'}/api/v1/:path*`,
      }
    ];
  },
};

export default nextConfig;

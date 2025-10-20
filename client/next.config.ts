import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Externalize PDF.js for server-side rendering (Next.js 15+)
  serverExternalPackages: ['pdfjs-dist'],
  
  // Configure webpack for React PDF
  webpack: (config, { isServer }) => {
    // Disable canvas for server-side (not needed)
    config.resolve.alias = {
      ...config.resolve.alias,
      canvas: false,
    };
    
    // Externalize canvas for all environments (PDF.js doesn't need it in browser)
    config.externals = config.externals || [];
    config.externals.push('canvas');
    
    // ✅ CRITICAL FIX: Configure file-loader for PDF.js worker files
    // This ensures worker files are properly bundled and served
    if (!isServer) {
      config.module = config.module || {};
      config.module.rules = config.module.rules || [];
      
      // Handle PDF.js worker files (.js)
      config.module.rules.push({
        test: /pdf\.worker\.(min\.)?js$/,
        type: 'asset/resource',
        generator: {
          filename: 'static/worker/[hash][ext][query]'
        }
      });
      
      // Handle PDF.js worker files (.mjs)
      config.module.rules.push({
        test: /pdf\.worker\.(min\.)?mjs$/,
        type: 'asset/resource',
        generator: {
          filename: 'static/worker/[hash][ext][query]'
        }
      });

      // Handle PDF.js legacy worker files
      config.module.rules.push({
        test: /pdf\.worker\.entry\.js$/,
        type: 'asset/resource',
        generator: {
          filename: 'static/worker/[hash][ext][query]'
        }
      });
    }
    
    return config;
  },
  
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ];
  },
  
  // CRITICAL: Enhanced CSP headers for Next.js 15 + React 19 + PDF.js compatibility
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'Content-Security-Policy',
            // Enhanced CSP for Chrome PDF plugin support + unpkg.com CDN worker
            value: [
              "default-src 'self' blob: data: http: https: ws: wss:",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob: data: https://unpkg.com",
              "style-src 'self' 'unsafe-inline' blob: data:",
              "frame-src 'self' blob: data: http: https:",
              "object-src 'self' blob: data:",        // CRITICAL FOR PDF
              "media-src 'self' blob: data:",         // CRITICAL FOR PDF
              "worker-src 'self' blob: data: https://unpkg.com",
              "child-src 'self' blob: data:",
              "connect-src 'self' http: https: ws: wss: https://unpkg.com",
              "img-src 'self' blob: data: https:",
              "font-src 'self' data: https:"
            ].join("; ")
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff'
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin'
          }
          // NOTE: X-Frame-Options intentionally omitted to allow iframe embedding
        ],
      },
    ];
  },

  // ✅ CRITICAL: React 19 compatibility settings for Next.js 15
  experimental: {
    reactCompiler: false, // Disable React Compiler until PDF.js is fully compatible
    ppr: false, // Disable Partial Prerendering for PDF components
  },
};

export default nextConfig;
